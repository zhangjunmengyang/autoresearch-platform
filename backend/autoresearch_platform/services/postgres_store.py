"""PostgreSQL-backed durable ResearchStore implementation."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any, Callable
from uuid import uuid4

from autoresearch_platform.services.store import (
    COLLECTIONS,
    COLLECTION_TABLES,
    REVIEWED_CURATION_SOURCE_TYPES,
    STATUSLESS_COLLECTIONS,
    JsonResearchStore,
)


ConnectionFactory = Callable[[], Any]


class PostgresResearchStore:
    """Durable store that persists platform JSON records in PostgreSQL tables."""

    def __init__(
        self,
        database_url: str | None,
        *,
        connection_factory: ConnectionFactory | None = None,
        dialect: str = "postgres",
    ) -> None:
        if not database_url:
            raise RuntimeError(
                "AUTORESEARCH_DATABASE_URL is required when AUTORESEARCH_STORE_BACKEND=postgres"
            )
        self.database_url = database_url
        self._connection_factory = connection_factory
        self._dialect = dialect

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _id(prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:12]}"

    @property
    def _placeholder(self) -> str:
        return "?" if self._dialect == "sqlite" else "%s"

    def _connect(self) -> Any:
        if self._connection_factory:
            return self._connection_factory()
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError("psycopg is required for PostgreSQL store deployments") from exc
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def _close_if_owned(self, connection: Any) -> None:
        if self._connection_factory:
            return
        connection.close()

    @staticmethod
    def _row_value(row: Any, key: str) -> Any:
        if isinstance(row, dict):
            return row.get(key)
        try:
            return row[key]
        except (KeyError, TypeError):
            return getattr(row, key)

    @staticmethod
    def _serialize_timestamp(value: Any) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    def _encode_payload(self, payload: dict[str, Any]) -> Any:
        if self._dialect == "sqlite":
            return json.dumps(payload, ensure_ascii=False, sort_keys=True)
        try:
            from psycopg.types.json import Jsonb
        except ImportError as exc:
            raise RuntimeError("psycopg JSONB support is required for PostgreSQL store deployments") from exc
        return Jsonb(payload)

    @staticmethod
    def _decode_payload(value: Any) -> dict[str, Any]:
        if value in {None, ""}:
            return {}
        if isinstance(value, str):
            return json.loads(value)
        return deepcopy(value)

    @staticmethod
    def _table(collection: str) -> str:
        table = COLLECTION_TABLES.get(collection)
        if not table:
            raise KeyError(collection)
        return table

    @staticmethod
    def _has_status(collection: str) -> bool:
        return collection not in STATUSLESS_COLLECTIONS

    def _payload_for_storage(self, collection: str, record: dict[str, Any]) -> dict[str, Any]:
        excluded = {"id", "title", "created_at", "updated_at"}
        if self._has_status(collection):
            excluded.add("status")
        return {key: deepcopy(value) for key, value in record.items() if key not in excluded}

    def _record_from_row(self, collection: str, row: Any) -> dict[str, Any]:
        record = self._decode_payload(self._row_value(row, "payload"))
        record["id"] = self._row_value(row, "id")
        record["title"] = self._row_value(row, "title")
        if self._has_status(collection):
            record["status"] = self._row_value(row, "status")
        record["created_at"] = self._serialize_timestamp(self._row_value(row, "created_at"))
        record["updated_at"] = self._serialize_timestamp(self._row_value(row, "updated_at"))
        return record

    def _fetch_all(self, sql: str, params: tuple[Any, ...] = ()) -> list[Any]:
        connection = self._connect()
        cursor = connection.cursor()
        try:
            cursor.execute(sql, params)
            return cursor.fetchall()
        finally:
            cursor.close()
            self._close_if_owned(connection)

    def _fetch_one(self, sql: str, params: tuple[Any, ...] = ()) -> Any | None:
        connection = self._connect()
        cursor = connection.cursor()
        try:
            cursor.execute(sql, params)
            return cursor.fetchone()
        finally:
            cursor.close()
            self._close_if_owned(connection)

    def _execute(self, sql: str, params: tuple[Any, ...]) -> None:
        connection = self._connect()
        cursor = connection.cursor()
        try:
            cursor.execute(sql, params)
            connection.commit()
        finally:
            cursor.close()
            self._close_if_owned(connection)

    def health(self) -> dict[str, Any]:
        collections: dict[str, int] = {}
        for collection, table in COLLECTION_TABLES.items():
            row = self._fetch_one(f"SELECT COUNT(*) AS count FROM {table}")
            collections[collection] = int(self._row_value(row, "count") if row is not None else 0)
        return {
            "store": "postgres",
            "status": "ready",
            "collections": collections,
        }

    def list_records(self, collection: str) -> list[dict[str, Any]]:
        table = self._table(collection)
        columns = "id, title, payload, created_at, updated_at"
        if self._has_status(collection):
            columns = "id, title, status, payload, created_at, updated_at"
        rows = self._fetch_all(f"SELECT {columns} FROM {table}")
        return [self._record_from_row(collection, row) for row in rows]

    def query_records(
        self,
        collection: str,
        *,
        status: str | None = None,
        q: str = "",
        limit: int = 50,
        offset: int = 0,
        sort: str = "-created_at",
    ) -> dict[str, Any]:
        items = self.list_records(collection)
        if status:
            items = [item for item in items if item.get("status") == status]
        if q:
            lowered = q.lower()
            items = [item for item in items if lowered in json.dumps(item, ensure_ascii=False).lower()]
        reverse = sort.startswith("-")
        key = sort[1:] if reverse else sort
        items.sort(key=lambda item: str(item.get(key, "")), reverse=reverse)
        limited = items[offset : offset + limit]
        return {"items": limited, "total": len(items), "limit": limit, "offset": offset, "sort": sort}

    def get_record(self, collection: str, record_id: str) -> dict[str, Any] | None:
        table = self._table(collection)
        columns = "id, title, payload, created_at, updated_at"
        if self._has_status(collection):
            columns = "id, title, status, payload, created_at, updated_at"
        row = self._fetch_one(f"SELECT {columns} FROM {table} WHERE id = {self._placeholder}", (record_id,))
        if row is None:
            return None
        return self._record_from_row(collection, row)

    def create_record(self, collection: str, prefix: str, payload: dict[str, Any]) -> dict[str, Any]:
        now = self._now()
        record = {
            "id": payload.get("id") or self._id(prefix),
            "created_at": now,
            "updated_at": now,
            **deepcopy(payload),
        }
        record.setdefault("title", "")
        if self._has_status(collection):
            record.setdefault("status", "planned")

        table = self._table(collection)
        marker = self._placeholder
        if self._has_status(collection):
            sql = f"""
                INSERT INTO {table} (id, title, status, payload, created_at, updated_at)
                VALUES ({marker}, {marker}, {marker}, {marker}, {marker}, {marker})
            """
            params = (
                record["id"],
                record["title"],
                record["status"],
                self._encode_payload(self._payload_for_storage(collection, record)),
                now,
                now,
            )
        else:
            sql = f"""
                INSERT INTO {table} (id, title, payload, created_at, updated_at)
                VALUES ({marker}, {marker}, {marker}, {marker}, {marker})
            """
            params = (
                record["id"],
                record["title"],
                self._encode_payload(self._payload_for_storage(collection, record)),
                now,
                now,
            )
        self._execute(sql, params)
        return deepcopy(record)

    def patch_record(self, collection: str, record_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self.get_record(collection, record_id)
        if not existing:
            raise KeyError(record_id)
        updated = deepcopy(existing)
        updated.update({key: value for key, value in payload.items() if value is not None})
        updated["updated_at"] = self._now()

        table = self._table(collection)
        marker = self._placeholder
        if self._has_status(collection):
            sql = f"""
                UPDATE {table}
                SET title = {marker}, status = {marker}, payload = {marker}, updated_at = {marker}
                WHERE id = {marker}
            """
            params = (
                updated.get("title", ""),
                updated.get("status", "planned"),
                self._encode_payload(self._payload_for_storage(collection, updated)),
                updated["updated_at"],
                record_id,
            )
        else:
            sql = f"""
                UPDATE {table}
                SET title = {marker}, payload = {marker}, updated_at = {marker}
                WHERE id = {marker}
            """
            params = (
                updated.get("title", ""),
                self._encode_payload(self._payload_for_storage(collection, updated)),
                updated["updated_at"],
                record_id,
            )
        self._execute(sql, params)
        return updated

    def create_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        session_id = payload.get("session_id") or self._id("session")
        session_payload = deepcopy(payload)
        session_payload.pop("session_id", None)
        return self.create_record("sessions", "session", {"id": session_id, **session_payload})

    def add_session_child(
        self,
        *,
        collection: str,
        prefix: str,
        session_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.get_record("sessions", session_id):
            raise KeyError(session_id)
        return self.create_record(collection, prefix, {"session_id": session_id, **deepcopy(payload)})

    def session_detail(self, session_id: str) -> dict[str, Any]:
        session = self.get_record("sessions", session_id)
        if not session:
            raise KeyError(session_id)
        return {
            "session": session,
            "events": [item for item in self.list_records("events") if item.get("session_id") == session_id],
            "experiments": [
                item for item in self.list_records("experiments") if item.get("session_id") == session_id
            ],
            "artifacts": [item for item in self.list_records("artifacts") if item.get("session_id") == session_id],
        }

    def close_session(self, session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        session = self.patch_record(
            "sessions",
            session_id,
            {
                "status": payload.get("status", "completed"),
                "closed_at": self._now(),
                "retrospective": payload.get("retrospective", {}),
                "source_refs": payload.get("source_refs", []),
                "generated_intake_item_ids": payload.get("generated_intake_item_ids", []),
            },
        )
        artifact = self.add_session_child(
            collection="artifacts",
            prefix="artifact",
            session_id=session_id,
            payload={
                "artifact_type": "retrospective",
                "title": f"{session.get('title', session_id)} retrospective",
                "summary": "Session close retrospective",
                "payload": payload.get("retrospective", {}),
                "source_refs": payload.get("source_refs", []),
            },
        )
        return {"session": session, "retrospective_artifact": artifact}

    def claim_intake(self, item_id: str, operator: str) -> dict[str, Any]:
        return self.patch_record(
            "intake_items",
            item_id,
            {"status": "claimed", "claimed_by": operator, "claimed_at": self._now()},
        )

    def start_session_from_intake(self, item_id: str) -> dict[str, Any]:
        item = self.get_record("intake_items", item_id)
        if not item:
            raise KeyError(item_id)
        session = self.create_session(
            {
                "title": item.get("title", "Untitled research"),
                "target": {"intake_item_id": item_id},
                "memory_context": {},
                "primary_path": "general-research",
                "information_gain": item.get("rationale", ""),
                "human_constraints": item.get("human_constraints", []),
                "source_refs": item.get("source_refs", []),
                "status": "planned",
            }
        )
        self.patch_record("intake_items", item_id, {"status": "running", "started_session_id": session["id"]})
        return session

    def query_experiences(self, query: str, topics: list[str], limit: int) -> dict[str, Any]:
        lowered = query.lower()
        matches = []
        for item in self.list_records("experiences"):
            text = json.dumps(item, ensure_ascii=False).lower()
            item_topics = set(item.get("topics", []) + item.get("tags", []))
            if lowered and lowered not in text:
                continue
            if topics and not item_topics.intersection(topics):
                continue
            matches.append(item)
        return {"items": deepcopy(matches[:limit]), "total": len(matches)}

    def _all_data(self) -> dict[str, list[dict[str, Any]]]:
        return {collection: self.list_records(collection) for collection in COLLECTIONS}

    def preview_curation(self, payload: dict[str, Any]) -> dict[str, Any]:
        warnings: list[str] = []
        source_refs = payload.get("source_refs") or []
        source_trace = JsonResearchStore._resolve_source_refs(self._all_data(), source_refs)

        governance_gaps: list[dict[str, Any]] = []
        if not payload.get("human_readable", True):
            warnings.append("human_readable=false: experience should be rewritten before apply")
        if not payload.get("runtime", {}).get("operator"):
            warnings.append("runtime.operator is recommended for auditability")
        if not source_refs:
            warnings.append("source_refs is required for durable experience curation")
            governance_gaps.append(
                {
                    "code": "missing_source_refs",
                    "severity": "blocking",
                    "message": "长期经验必须绑定平台内来源引用。",
                }
            )
        if source_trace["unresolved"]:
            warnings.append(f"unresolved source_refs: {len(source_trace['unresolved'])}")
            governance_gaps.append(
                {
                    "code": "unresolved_source_refs",
                    "severity": "blocking",
                    "message": "部分来源引用无法在平台事实账本中解析。",
                    "refs": source_trace["unresolved"],
                }
            )
        if source_trace["resolved"] and not REVIEWED_CURATION_SOURCE_TYPES.intersection(
            source_trace["coverage"]
        ):
            governance_gaps.append(
                {
                    "code": "weak_curation_sources",
                    "severity": "warning",
                    "message": "当前来源尚未包含 evidence、review 或 decision，沉淀长期经验前建议补一条已审查证据链。",
                }
            )
        if not payload.get("experience", {}).get("title"):
            warnings.append("experience.title is required")
        if payload.get("action") in {"update", "supersede"}:
            experience = payload.get("experience", {})
            if not experience.get("id") and not experience.get("supersedes"):
                warnings.append("update or supersede requires experience.id or experience.supersedes")
        accepted = not warnings and not any(gap["severity"] == "blocking" for gap in governance_gaps)
        return {
            "accepted": accepted,
            "warnings": warnings,
            "source_trace": source_trace,
            "governance_gaps": governance_gaps,
            "recommended_next_actions": JsonResearchStore._curation_next_actions(
                accepted=accepted,
                governance_gaps=governance_gaps,
            ),
            "safety": "read_only_curation_preview_no_auto_extraction",
            "payload": payload,
        }

    def apply_curation(self, payload: dict[str, Any]) -> dict[str, Any]:
        preview = self.preview_curation(payload)
        if not payload.get("source_refs"):
            raise ValueError("source_refs is required for durable experience curation")
        if any(gap["severity"] == "blocking" for gap in preview["governance_gaps"]):
            raise ValueError("unresolved source_refs must be fixed before durable experience curation")

        action = payload.get("action", "create")
        experience = deepcopy(payload.get("experience", {}))
        experience["curation"] = {
            "runtime": payload.get("runtime", {}),
            "source_refs": payload.get("source_refs", []),
            "warnings": preview["warnings"],
        }
        experience.setdefault("kind", "finding")
        experience.setdefault("title", experience.get("problem", "Untitled experience"))

        if action == "update":
            experience_id = experience.get("id")
            if not experience_id:
                raise ValueError("update requires experience.id")
            experience.setdefault("status", "candidate")
            record = self.patch_record("experiences", experience_id, experience)
        elif action == "reject":
            experience.setdefault("status", "rejected")
            experience_id = experience.get("id")
            if experience_id:
                record = self.patch_record("experiences", experience_id, experience)
            else:
                record = self.create_record("experiences", "experience", experience)
        elif action == "supersede":
            supersedes = experience.get("supersedes") or experience.get("id")
            if not supersedes:
                raise ValueError("supersede requires experience.supersedes or experience.id")
            self.patch_record("experiences", supersedes, {"status": "superseded"})
            experience["supersedes"] = supersedes
            experience.pop("id", None)
            experience.setdefault("status", "candidate")
            record = self.create_record("experiences", "experience", experience)
        elif action == "topic_summary":
            topic_id = experience.get("id") or experience.get("topic") or experience.get("title")
            if not topic_id:
                raise ValueError("topic_summary requires experience.id, experience.topic or experience.title")
            topic_payload = {"id": topic_id, **experience}
            existing = self.get_record("experience_topics", topic_id)
            if existing:
                record = self.patch_record("experience_topics", topic_id, topic_payload)
            else:
                record = self.create_record("experience_topics", "topic", topic_payload)
        else:
            experience.setdefault("status", "candidate")
            record = self.create_record("experiences", "experience", experience)
        return {
            "experience": record,
            "warnings": preview["warnings"],
            "source_trace": preview["source_trace"],
            "governance_gaps": preview["governance_gaps"],
        }

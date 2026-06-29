"""Small durable JSON store for the v1 local platform."""

from __future__ import annotations

import json
import threading
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4


COLLECTIONS = [
    "sources",
    "insights",
    "hypotheses",
    "research_programs",
    "research_questions",
    "method_cards",
    "protocols",
    "intake_items",
    "sessions",
    "research_rounds",
    "events",
    "experiments",
    "artifacts",
    "benchmarks",
    "benchmark_runs",
    "evidence_records",
    "reviews",
    "decisions",
    "experiences",
    "experience_topics",
    "logs",
    "log_topics",
]

COLLECTION_TABLES = {
    "sources": "research_sources",
    "insights": "research_insights",
    "hypotheses": "research_hypotheses",
    "research_programs": "research_programs",
    "research_questions": "research_questions",
    "method_cards": "method_cards",
    "protocols": "protocols",
    "intake_items": "research_intake_items",
    "sessions": "research_sessions",
    "research_rounds": "research_rounds",
    "events": "research_events",
    "experiments": "research_experiments",
    "artifacts": "research_artifacts",
    "benchmarks": "benchmarks",
    "benchmark_runs": "benchmark_runs",
    "evidence_records": "evidence_records",
    "reviews": "reviews",
    "decisions": "decisions",
    "experiences": "experiences",
    "experience_topics": "experience_topics",
    "logs": "logs",
    "log_topics": "log_topics",
}

STATUSLESS_COLLECTIONS = {
    "sources",
    "insights",
    "events",
    "artifacts",
    "experience_topics",
    "logs",
    "log_topics",
}

SOURCE_REF_TARGETS = {
    "source": ("source", "sources"),
    "insight": ("insight", "insights"),
    "hypothesis": ("hypothesis", "hypotheses"),
    "research_program": ("research_program", "research_programs"),
    "program": ("research_program", "research_programs"),
    "research_question": ("research_question", "research_questions"),
    "question": ("research_question", "research_questions"),
    "method_card": ("method_card", "method_cards"),
    "protocol": ("protocol", "protocols"),
    "intake_item": ("intake_item", "intake_items"),
    "session": ("session", "sessions"),
    "research_session": ("session", "sessions"),
    "research_round": ("research_round", "research_rounds"),
    "round": ("research_round", "research_rounds"),
    "event": ("event", "events"),
    "experiment": ("experiment", "experiments"),
    "research_experiment": ("experiment", "experiments"),
    "artifact": ("artifact", "artifacts"),
    "benchmark": ("benchmark", "benchmarks"),
    "benchmark_run": ("benchmark_run", "benchmark_runs"),
    "evidence_record": ("evidence_record", "evidence_records"),
    "evidence": ("evidence_record", "evidence_records"),
    "review": ("review", "reviews"),
    "decision": ("decision", "decisions"),
    "experience": ("experience", "experiences"),
    "experience_topic": ("experience_topic", "experience_topics"),
}

REVIEWED_CURATION_SOURCE_TYPES = {"evidence_record", "review", "decision"}


class ResearchStore(Protocol):
    def health(self) -> dict[str, Any]: ...

    def list_records(self, collection: str) -> list[dict[str, Any]]: ...

    def query_records(
        self,
        collection: str,
        *,
        status: str | None = None,
        q: str = "",
        limit: int = 50,
        offset: int = 0,
        sort: str = "-created_at",
    ) -> dict[str, Any]: ...

    def get_record(self, collection: str, record_id: str) -> dict[str, Any] | None: ...

    def create_record(self, collection: str, prefix: str, payload: dict[str, Any]) -> dict[str, Any]: ...

    def patch_record(self, collection: str, record_id: str, payload: dict[str, Any]) -> dict[str, Any]: ...

    def create_session(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    def add_session_child(
        self,
        *,
        collection: str,
        prefix: str,
        session_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]: ...

    def session_detail(self, session_id: str) -> dict[str, Any]: ...

    def close_session(self, session_id: str, payload: dict[str, Any]) -> dict[str, Any]: ...

    def claim_intake(self, item_id: str, operator: str) -> dict[str, Any]: ...

    def start_session_from_intake(self, item_id: str) -> dict[str, Any]: ...

    def query_experiences(self, query: str, topics: list[str], limit: int) -> dict[str, Any]: ...

    def preview_curation(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    def apply_curation(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class JsonResearchStore:
    """Thread-safe JSON-backed store.

    This is intentionally simple: it gives the new project a complete local
    workflow before a deployment chooses PostgreSQL. The public contract is the
    REST API, not this storage adapter.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({name: [] for name in COLLECTIONS})

    def _read(self) -> dict[str, list[dict[str, Any]]]:
        with self.path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return {name: data.get(name, []) for name in COLLECTIONS}

    def _write(self, data: dict[str, list[dict[str, Any]]]) -> None:
        tmp = self.path.with_name(f"{self.path.name}.{uuid4().hex}.tmp")
        try:
            with tmp.open("w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
            tmp.replace(self.path)
        finally:
            tmp.unlink(missing_ok=True)

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _id(prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:12]}"

    def health(self) -> dict[str, Any]:
        with self._lock:
            data = self._read()
            return {
                "store": "json",
                "path": str(self.path),
                "collections": {name: len(data[name]) for name in COLLECTIONS},
            }

    def list_records(self, collection: str) -> list[dict[str, Any]]:
        with self._lock:
            return deepcopy(self._read()[collection])

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
        with self._lock:
            items = deepcopy(self._read()[collection])
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
        with self._lock:
            for item in self._read()[collection]:
                if item.get("id") == record_id:
                    return deepcopy(item)
        return None

    def create_record(self, collection: str, prefix: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            data = self._read()
            now = self._now()
            record = {
                "id": payload.pop("id", None) or self._id(prefix),
                "created_at": now,
                "updated_at": now,
                **payload,
            }
            data[collection].append(record)
            self._write(data)
            return deepcopy(record)

    def patch_record(self, collection: str, record_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            data = self._read()
            for item in data[collection]:
                if item.get("id") == record_id:
                    item.update({key: value for key, value in payload.items() if value is not None})
                    item["updated_at"] = self._now()
                    self._write(data)
                    return deepcopy(item)
        raise KeyError(record_id)

    def create_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        session_id = payload.pop("session_id", None) or self._id("session")
        return self.create_record("sessions", "session", {"id": session_id, **payload})

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
        return self.create_record(collection, prefix, {"session_id": session_id, **payload})

    def session_detail(self, session_id: str) -> dict[str, Any]:
        session = self.get_record("sessions", session_id)
        if not session:
            raise KeyError(session_id)
        with self._lock:
            data = self._read()
            return {
                "session": session,
                "events": [item for item in data["events"] if item.get("session_id") == session_id],
                "experiments": [
                    item for item in data["experiments"] if item.get("session_id") == session_id
                ],
                "artifacts": [item for item in data["artifacts"] if item.get("session_id") == session_id],
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
        with self._lock:
            items = self._read()["experiences"]
        matches = []
        for item in items:
            text = json.dumps(item, ensure_ascii=False).lower()
            item_topics = set(item.get("topics", []) + item.get("tags", []))
            if lowered and lowered not in text:
                continue
            if topics and not item_topics.intersection(topics):
                continue
            matches.append(item)
        return {"items": deepcopy(matches[:limit]), "total": len(matches)}

    @staticmethod
    def _source_ref_record_summary(record: dict[str, Any]) -> str:
        for key in ("title", "summary", "claim", "decision", "hypothesis", "name", "event_type"):
            value = record.get(key)
            if value:
                return str(value)
        return record.get("id", "")

    @classmethod
    def _resolve_source_refs(
        cls,
        data: dict[str, list[dict[str, Any]]],
        source_refs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        resolved: list[dict[str, Any]] = []
        unresolved: list[dict[str, Any]] = []
        coverage: dict[str, int] = {}

        for ref in source_refs:
            ref_type = str(ref.get("type") or "").strip()
            record_id = ref.get("id") or ref.get("record_id")
            if not ref_type:
                unresolved.append({"type": "unknown", "id": record_id, "reason": "missing_type"})
                continue
            target = SOURCE_REF_TARGETS.get(ref_type)
            if not target:
                unresolved.append({"type": ref_type, "id": record_id, "reason": "unknown_type"})
                continue
            canonical_type, collection = target
            if not record_id:
                unresolved.append({"type": canonical_type, "id": None, "reason": "missing_id"})
                continue
            record = next(
                (item for item in data.get(collection, []) if item.get("id") == record_id),
                None,
            )
            if not record:
                unresolved.append({"type": canonical_type, "id": record_id, "reason": "record_not_found"})
                continue
            coverage[canonical_type] = coverage.get(canonical_type, 0) + 1
            resolved.append(
                {
                    "type": canonical_type,
                    "id": record_id,
                    "collection": collection,
                    "status": record.get("status"),
                    "summary": cls._source_ref_record_summary(record),
                }
            )

        return {"resolved": resolved, "unresolved": unresolved, "coverage": coverage}

    @staticmethod
    def _curation_next_actions(
        *,
        accepted: bool,
        governance_gaps: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        gap_codes = {gap["code"] for gap in governance_gaps}
        actions: list[dict[str, str]] = []
        if "missing_source_refs" in gap_codes:
            actions.append(
                {
                    "action": "attach_source_refs",
                    "endpoint": "POST /api/v1/evidence-records",
                    "reason": "先登记 evidence、artifact、review 或 decision，再把引用写入 curation payload。",
                }
            )
        if "unresolved_source_refs" in gap_codes:
            actions.append(
                {
                    "action": "fix_source_refs",
                    "endpoint": "POST /api/v1/experiences/curation/preview",
                    "reason": "修正找不到的来源引用后重新预检。",
                }
            )
        if "weak_curation_sources" in gap_codes:
            actions.append(
                {
                    "action": "add_reviewed_source",
                    "endpoint": "POST /api/v1/evidence-records",
                    "reason": "长期经验最好至少绑定 evidence、review 或 decision 之一。",
                }
            )
        if accepted:
            actions.append(
                {
                    "action": "apply_curation",
                    "endpoint": "POST /api/v1/experiences/curation/apply",
                    "reason": "预检通过后显式写入长期经验。",
                }
            )
        return actions

    def preview_curation(self, payload: dict[str, Any]) -> dict[str, Any]:
        warnings: list[str] = []
        source_refs = payload.get("source_refs") or []
        with self._lock:
            source_trace = self._resolve_source_refs(self._read(), source_refs)

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
            "recommended_next_actions": self._curation_next_actions(
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

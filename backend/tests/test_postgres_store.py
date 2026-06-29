from __future__ import annotations

import sqlite3

from autoresearch_platform.services import PostgresResearchStore
from autoresearch_platform.services.store import COLLECTION_TABLES


STATUSLESS_COLLECTIONS = {
    "sources",
    "insights",
    "events",
    "artifacts",
    "experience_topics",
    "logs",
    "log_topics",
}


def _create_sqlite_schema(connection: sqlite3.Connection) -> None:
    for collection, table in COLLECTION_TABLES.items():
        status_column = "" if collection in STATUSLESS_COLLECTIONS else "status TEXT NOT NULL DEFAULT 'planned',"
        connection.execute(
            f"""
            CREATE TABLE {table} (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT '',
                {status_column}
                payload TEXT NOT NULL DEFAULT '{{}}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
    connection.commit()


def test_postgres_store_roundtrips_core_research_records_with_platform_text_ids():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    _create_sqlite_schema(connection)
    store = PostgresResearchStore(
        "postgresql://example/autoresearch",
        connection_factory=lambda: connection,
        dialect="sqlite",
    )

    source = store.create_record(
        "sources",
        "source",
        {
            "id": "source_manual",
            "kind": "paper",
            "title": "Memory paper",
            "uri": "https://example.test/paper",
        },
    )
    assert source["id"] == "source_manual"
    assert source["kind"] == "paper"
    assert source["uri"] == "https://example.test/paper"

    patched_source = store.patch_record("sources", "source_manual", {"summary": "reviewed source"})
    assert patched_source["summary"] == "reviewed source"
    assert store.get_record("sources", "source_manual")["summary"] == "reviewed source"
    assert store.query_records("sources", q="reviewed")["total"] == 1

    session = store.create_session(
        {
            "session_id": "session_manual",
            "title": "Memory replay run",
            "status": "planned",
            "target": {"claim": "replay helps recall"},
        }
    )
    event = store.add_session_child(
        collection="events",
        prefix="event",
        session_id=session["id"],
        payload={"event_type": "observation", "summary": "external runtime observed blocker"},
    )
    experiment = store.add_session_child(
        collection="experiments",
        prefix="experiment",
        session_id=session["id"],
        payload={"title": "Replay benchmark", "status": "completed", "metrics": {"recall": 0.72}},
    )

    detail = store.session_detail(session["id"])
    assert detail["session"]["target"]["claim"] == "replay helps recall"
    assert detail["events"][0]["id"] == event["id"]
    assert detail["experiments"][0]["id"] == experiment["id"]

    closed = store.close_session(
        session["id"],
        {
            "status": "degraded",
            "retrospective": {"platform_gaps": ["needs durable adapter"]},
            "source_refs": [{"type": "source", "id": "source_manual"}],
        },
    )
    assert closed["session"]["status"] == "degraded"
    assert closed["retrospective_artifact"]["artifact_type"] == "retrospective"
    assert store.health()["status"] == "ready"
    assert store.health()["collections"]["sources"] == 1

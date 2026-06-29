from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import autoresearch_platform.main as main_module
from autoresearch_platform.core.config import Settings
from autoresearch_platform.main import app
from autoresearch_platform.routes.v1.api import build_system_readiness
from autoresearch_platform.services import JsonResearchStore


client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_store(tmp_path):
    original_store = main_module.store
    main_module.store = JsonResearchStore(tmp_path / "autoresearch_store.json")
    try:
        yield
    finally:
        main_module.store = original_store


def _data(response):
    assert response.status_code < 400, response.text
    return response.json()["data"]


def test_openapi_exposes_agent_metadata_for_all_public_operations():
    schema = app.openapi()
    assert "/api/v1/openapi.json" == schema["x-agent-entrypoint"]["openapi"]
    assert schema["x-agent-entrypoint"]["base_path"] == "/api/v1"
    assert "GET /api/v1/capabilities" in schema["x-agent-entrypoint"]["recommended_first_calls"]
    assert "GET /api/v1/system/security" in schema["x-agent-entrypoint"]["recommended_first_calls"]
    assert schema["x-agent-entrypoint"]["auth"]["scheme"] == "optional_bearer_token"
    assert "BearerAuth" in schema["components"]["securitySchemes"]
    assert schema["x-agent-capabilities"]

    missing = []
    for path, methods in schema["paths"].items():
        for method, operation in methods.items():
            if method not in {"get", "post", "patch", "put", "delete"}:
                continue
            for key in [
                "x-agent-guidance",
                "x-capability-group",
                "x-safety-level",
                "x-agent-visible",
                "x-response-contract",
            ]:
                if key not in operation:
                    missing.append((method, path, key))
    assert missing == []


def test_system_status_reports_store_mode():
    status = _data(client.get("/api/v1/system/status"))
    assert status["store"] in {"json", "postgres"}


def test_system_readiness_reports_store_and_schema_contract():
    readiness = _data(client.get("/api/v1/system/readiness"))

    assert readiness["safety"] == "read_only_deployment_readiness_no_external_access"
    assert readiness["state"] == "degraded"
    assert readiness["schema_contract"]["covers_store_collections"] is True
    check_statuses = {check["id"]: check["status"] for check in readiness["checks"]}
    assert check_statuses["store_access"] == "pass"
    assert check_statuses["durable_store"] == "warn"
    assert check_statuses["platform_text_id_contract"] == "pass"
    assert check_statuses["schema_collection_coverage"] == "pass"
    assert any(
        action["endpoint"] == "docs/architecture/reference.md"
        for action in readiness["recommended_next_actions"]
    )


def test_system_readiness_accepts_connected_postgres_store():
    class ReadyPostgresStore:
        def health(self):
            return {
                "store": "postgres",
                "status": "ready",
                "collections": {},
            }

    readiness = build_system_readiness(ReadyPostgresStore())

    assert readiness["state"] == "ready"
    check_statuses = {check["id"]: check["status"] for check in readiness["checks"]}
    assert check_statuses["durable_store"] == "pass"
    assert check_statuses["schema_collection_coverage"] == "pass"
    assert readiness["recommended_next_actions"] == []


def test_agent_onboarding_bundle_summarizes_public_entrypoints_and_skill_refs():
    onboarding = _data(client.get("/api/v1/agent/onboarding"))

    assert onboarding["schema"] == "autoresearch.agent_onboarding.v1"
    assert onboarding["state"] == "degraded"
    assert onboarding["openapi"] == "/api/v1/openapi.json"
    assert onboarding["safety"] == "read_only_onboarding_no_execution_no_external_access"
    assert onboarding["security"]["auth_required"] is False
    assert onboarding["readiness"]["state"] == "degraded"
    assert onboarding["capability_count"] == len(app.openapi()["x-agent-capabilities"])
    assert onboarding["capability_groups"]["method_loop"]["primary_endpoint"] == "GET /api/v1/method-loop"
    assert onboarding["capability_groups"]["research_methodology"]["primary_endpoint"] == "POST /api/v1/research/programs"
    assert onboarding["capability_groups"]["research_audit"]["primary_endpoint"] == "GET /api/v1/research/events"
    assert onboarding["skill"]["name"] == "auto-research"
    assert "references/bootstrap.md" in onboarding["skill"]["load_order"]
    assert "references/safety-boundaries.md" in onboarding["skill"]["load_order"]
    assert "GET /api/v1/agent/onboarding" in onboarding["recommended_first_calls"]
    assert "GET /api/v1/method-loop" in onboarding["recommended_first_calls"]
    assert "GET /api/v1/system/security" in onboarding["recommended_first_calls"]
    assert "GET /api/v1/research/design/audit" in onboarding["recommended_first_calls"]
    assert any(action["endpoint"] == "docs/architecture/reference.md" for action in onboarding["recommended_next_actions"])
    assert onboarding["integrity"]["external_reads"] is False
    assert onboarding["integrity"]["external_writes"] is False
    assert onboarding["integrity"]["executes_runtime"] is False


def test_research_method_templates_are_read_only_design_guides():
    response = client.get("/api/v1/research/method-templates")
    assert response.status_code == 200
    templates = response.json()["data"]

    assert templates["schema"] == "autoresearch.method_templates.v1"
    assert templates["state"] == "ready"
    assert templates["safety"] == "read_only_methodology_templates_no_execution"
    assert templates["recommended_next_actions"][0]["endpoint"] == "POST /api/v1/research/method-cards"
    template_ids = {template["id"] for template in templates["templates"]}
    assert {
        "literature_synthesis",
        "reproduction",
        "ablation",
        "benchmark_comparison",
        "failure_analysis",
    } <= template_ids

    reproduction = next(template for template in templates["templates"] if template["id"] == "reproduction")
    assert reproduction["title"] == "复现实验"
    assert "POST /api/v1/research/protocols" in reproduction["next_endpoints"]
    assert "POST /api/v1/evidence-records" in reproduction["next_endpoints"]
    assert "baseline_artifact" in reproduction["required_records"]
    assert reproduction["protocol_defaults"]["one_change"] == "复现目标或环境固定，先不引入新方法变化"
    assert "run_log" in reproduction["artifact_requirements"]
    assert reproduction["safety"]["executes_experiment"] is False
    assert reproduction["safety"]["creates_workflow_dag"] is False

    operation = app.openapi()["paths"]["/api/v1/research/method-templates"]["get"]
    assert operation["x-capability-group"] == "research_methodology"
    assert operation["x-safety-level"] == "read"
    assert operation["x-agent-visible"] is True
    assert "x-agent-guidance" in operation
    assert "templates" in operation["x-response-contract"]


def test_settings_accepts_comma_separated_or_json_cors_origins(monkeypatch):
    monkeypatch.setenv("AUTORESEARCH_CORS_ORIGINS", "http://127.0.0.1:5174,http://localhost:5174")
    comma_settings = Settings(_env_file=None)
    assert comma_settings.cors_origins == ["http://127.0.0.1:5174", "http://localhost:5174"]

    monkeypatch.setenv("AUTORESEARCH_CORS_ORIGINS", '["http://127.0.0.1:5185"]')
    json_settings = Settings(_env_file=None)
    assert json_settings.cors_origins == ["http://127.0.0.1:5185"]


def test_optional_api_token_protects_research_data_and_audits_write_attempts(monkeypatch):
    monkeypatch.setattr(main_module.settings, "api_token", "secret-token")

    assert client.get("/api/v1/capabilities").status_code == 200
    assert client.get("/api/v1/agent/onboarding").status_code == 200
    assert client.get("/api/v1/method-loop").status_code == 200
    assert client.get("/api/v1/system/security").status_code == 200
    assert client.get("/api/v1/sources").status_code == 401

    denied = client.post(
        "/api/v1/sources",
        json={"kind": "paper", "title": "Secret paper", "uri": "https://example.test/private"},
    )
    assert denied.status_code == 401

    created = _data(
        client.post(
            "/api/v1/sources",
            headers={
                "Authorization": "Bearer secret-token",
                "X-Autoresearch-Actor": "external-agent-a",
            },
            json={"kind": "paper", "title": "Secret paper", "uri": "https://example.test/private"},
        )
    )
    assert created["title"] == "Secret paper"

    audit_log = _data(
        client.get(
            "/api/v1/system/audit-log",
            headers={"Authorization": "Bearer secret-token"},
        )
    )
    assert audit_log["total"] >= 2
    audit_text = json.dumps(audit_log, ensure_ascii=False)
    assert "Secret paper" not in audit_text
    assert "https://example.test/private" not in audit_text
    assert any(item["event_type"] == "api_request" for item in audit_log["items"])
    assert any(item["status_code"] == 401 for item in audit_log["items"])
    assert any(item["actor"] == "external-agent-a" for item in audit_log["items"])

    security = _data(client.get("/api/v1/system/security"))
    assert security["auth_required"] is True
    assert "secret-token" not in json.dumps(security, ensure_ascii=False)


def test_public_openapi_uses_only_platform_capability_groups():
    schema = app.openapi()
    allowed_groups = {
        "artifact_registry",
        "benchmark_registry",
        "capabilities",
        "method_loop",
        "decision_records",
        "evidence_records",
            "experience_curation",
            "platform_readiness",
            "research_audit",
        "research_intake",
        "research_methodology",
        "research_round_ledger",
        "research_session_ledger",
        "review_events",
        "runtime_event_ledger",
        "source_to_insight",
        "system",
    }
    capability_ids = {capability["id"] for capability in schema["x-agent-capabilities"]}
    assert capability_ids <= allowed_groups

    operation_groups = set()
    for methods in schema["paths"].values():
        for method, operation in methods.items():
            if method not in {"get", "post", "patch", "put", "delete"}:
                continue
            operation_groups.add(operation["x-capability-group"])
    assert operation_groups <= allowed_groups


def test_postgres_schema_uses_platform_text_ids_not_uuid_surrogates():
    migration_text = Path("migrations/versions/20260629_0001_initial_autoresearch_schema.py").read_text()

    assert "id TEXT PRIMARY KEY" in migration_text
    assert "id UUID" not in migration_text
    assert "gen_random_uuid" not in migration_text
    assert "CREATE EXTENSION IF NOT EXISTS pgcrypto" not in migration_text
    assert "payload JSONB NOT NULL" in migration_text


def test_postgres_schema_covers_all_store_collections():
    migration_text = Path("migrations/versions/20260629_0001_initial_autoresearch_schema.py").read_text()
    expected_tables = {
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

    missing_tables = [
        table
        for table in expected_tables.values()
        if f'_json_table("{table}"' not in migration_text
    ]
    assert missing_tables == []


def test_postgres_deployment_reads_database_url_and_runs_migrations():
    alembic_env = Path("migrations/env.py").read_text()
    compose_text = Path("../docker-compose.yml").read_text()

    assert "AUTORESEARCH_DATABASE_URL" in alembic_env
    assert "postgresql+psycopg://" in alembic_env
    assert "alembic upgrade head" in compose_text


def test_source_to_session_to_artifact_close_loop():
    source = _data(
        client.post(
            "/api/v1/sources",
            json={"kind": "paper", "title": "Memory Agents", "uri": "https://example.test/paper"},
        )
    )
    insight = _data(
        client.post(
            "/api/v1/insights",
            json={
                "title": "Long horizon memory needs replay",
                "body": "Benchmark must include delayed recall.",
                "source_refs": [{"type": "source", "id": source["id"]}],
            },
        )
    )
    hypothesis = _data(
        client.post(
            "/api/v1/hypotheses",
            json={
                "title": "Replay improves recall",
                "hypothesis": "Nightly memory replay improves benchmark recall.",
                "expected_effect": "recall@10 improves",
                "acceptance_criteria": {"recall_delta_gt": 0.05},
                "rejection_criteria": {"latency_delta_gt": 0.2},
                "insight_refs": [insight["id"]],
            },
        )
    )
    intake = _data(
        client.post(
            "/api/v1/research/intake",
            json={
                "title": "Validate memory replay",
                "rationale": "Human asked to verify agent memory.",
                "hypothesis_refs": [hypothesis["id"]],
                "human_constraints": ["Do not change model provider."],
            },
        )
    )
    claimed = _data(client.post(f"/api/v1/research/intake/{intake['id']}/claim?operator=tester"))
    assert claimed["status"] == "claimed"

    session = _data(client.post(f"/api/v1/research/intake/{intake['id']}/start-session"))
    event = _data(
        client.post(
            f"/api/v1/research/sessions/{session['id']}/events",
            json={
                "event_type": "human_instruction",
                "title": "User requested recall benchmark",
                "payload": {"source": "chat"},
            },
        )
    )
    assert event["session_id"] == session["id"]

    experiment = _data(
        client.post(
            f"/api/v1/research/sessions/{session['id']}/experiments",
            json={
                "hypothesis": "Replay improves recall",
                "expected_effect": "recall@10 improves",
                "acceptance_criteria": {"recall_delta_gt": 0.05},
                "rejection_criteria": {"latency_delta_gt": 0.2},
            },
        )
    )
    patched = _data(
        client.patch(
            f"/api/v1/research/sessions/{session['id']}/experiments/{experiment['id']}",
            json={"status": "degraded", "result_summary": "Runner missing one dataset shard."},
        )
    )
    assert patched["status"] == "degraded"

    artifact = _data(
        client.post(
            f"/api/v1/research/sessions/{session['id']}/artifacts",
            json={
                "artifact_type": "benchmark_result",
                "title": "Replay recall smoke",
                "summary": "Partial result retained as degraded evidence.",
            },
        )
    )
    close = _data(
        client.post(
            f"/api/v1/research/sessions/{session['id']}/close",
            json={
                "status": "degraded",
                "retrospective": {
                    "failed_attempts": ["dataset shard unavailable"],
                    "platform_gaps": [],
                    "next_agent_one_liner": "Restore shard before formal benchmark.",
                },
                "source_refs": [{"type": "artifact", "id": artifact["id"]}],
            },
        )
    )
    assert close["session"]["status"] == "degraded"
    detail = _data(client.get(f"/api/v1/research/sessions/{session['id']}"))
    assert len(detail["events"]) >= 1
    assert len(detail["experiments"]) == 1
    assert len(detail["artifacts"]) >= 2


def test_method_loop_endpoints_map_to_backing_collections():
    loop = _data(client.get("/api/v1/method-loop"))
    assert loop["schema"] == "autoresearch.method_loop.v1"
    assert [stage["label"] for stage in loop["stages"]] == [
        "Idea Pool",
        "Hypothesis",
        "Plan",
        "Experiment",
        "Result",
        "Review",
        "Decision",
        "Lesson",
    ]
    assert loop["safety"]["executes_runtime"] is False

    idea = _data(
        client.post(
            "/api/v1/ideas",
            json={
                "kind": "researcher_idea",
                "title": "Try retrieval reranking",
                "summary": "Researcher thinks reranking may improve long-tail cases.",
                "tags": ["retrieval"],
            },
        )
    )
    assert idea["id"].startswith("idea_")
    assert idea["metadata"]["loop_stage"] == "idea_pool"

    hypothesis = _data(
        client.post(
            "/api/v1/hypotheses",
            json={
                "title": "Reranking improves long-tail recall",
                "hypothesis": "A lightweight reranker improves recall on long-tail benchmark cases.",
                "expected_effect": "recall@10 improves",
                "acceptance_criteria": {"recall_delta_gt": 0.02},
                "rejection_criteria": {"latency_delta_gt": 0.1},
                "source_refs": [{"type": "source", "id": idea["id"]}],
            },
        )
    )

    plan = _data(
        client.post(
            "/api/v1/plans",
            json={
                "title": "Reranking ablation",
                "hypothesis_id": hypothesis["id"],
                "objective": "Validate reranking against the current benchmark baseline.",
                "one_change": "Enable reranker after retrieval.",
                "validation_method": "benchmark_comparison",
                "controls": ["baseline retrieval"],
                "acceptance_criteria": {"recall_delta_gt": 0.02},
                "rejection_criteria": {"latency_delta_gt": 0.1},
                "result_requirements": ["score_report", "badcase_summary"],
            },
        )
    )
    assert plan["id"].startswith("plan_")
    assert plan["metadata"]["loop_stage"] == "plan"
    assert "score_report" in plan["artifact_requirements"]

    result = _data(
        client.post(
            "/api/v1/results",
            json={
                "result_type": "benchmark_result",
                "title": "Reranking benchmark result",
                "summary": "recall@10 improved by 0.03 with acceptable latency.",
                "uri": "s3://bucket/rerank-result.json",
                "sha256": "a" * 64,
                "size_bytes": 2048,
                "metrics": {"recall_at_10_delta": 0.03},
                "source_refs": [{"type": "hypothesis", "id": hypothesis["id"]}],
            },
        )
    )
    assert result["id"].startswith("result_")
    assert result["artifact_type"] == "benchmark_result"
    assert result["metadata"]["loop_stage"] == "result"
    assert result["payload"]["metrics"]["recall_at_10_delta"] == 0.03

    applied = _data(
        client.post(
            "/api/v1/experiences/curation/apply",
            json={
                "action": "create",
                "runtime": {"operator": "external-runtime"},
                "experience": {
                    "title": "Reranking helped long-tail recall",
                    "body": "Use reranking when long-tail retrieval cases dominate failures.",
                    "tags": ["retrieval"],
                },
                "source_refs": [{"type": "artifact", "id": result["id"]}],
            },
        )
    )
    lesson_id = applied["experience"]["id"]
    lessons = _data(client.get("/api/v1/lessons?q=Reranking&limit=10"))
    assert any(item["id"] == lesson_id for item in lessons["items"])


def test_list_endpoints_support_status_filter_limit_offset_and_sort():
    first = _data(client.post("/api/v1/research/intake", json={"title": "A", "status": "queued"}))
    second = _data(client.post("/api/v1/research/intake", json={"title": "B", "status": "blocked"}))

    filtered = _data(
        client.get("/api/v1/research/intake?status=blocked&limit=10&offset=0&sort=-created_at")
    )

    assert filtered["total"] >= 1
    assert filtered["limit"] == 10
    assert filtered["offset"] == 0
    assert filtered["sort"] == "-created_at"
    assert any(item["id"] == second["id"] for item in filtered["items"])
    assert all(item["status"] == "blocked" for item in filtered["items"])
    assert all(item["id"] != first["id"] for item in filtered["items"])


def test_artifact_registration_requires_reference_not_large_payload():
    session = _data(
        client.post(
            "/api/v1/research/sessions",
            json={"title": "artifact policy", "information_gain": "policy test"},
        )
    )
    response = client.post(
        f"/api/v1/research/sessions/{session['id']}/artifacts",
        json={
            "artifact_type": "dataset",
            "title": "bad inline artifact",
            "payload": {"raw_content": "x" * 20000},
        },
    )
    assert response.status_code == 422

    artifact = _data(
        client.post(
            f"/api/v1/research/sessions/{session['id']}/artifacts",
            json={
                "artifact_type": "dataset_ref",
                "title": "external dataset reference",
                "uri": "s3://bucket/dataset.parquet",
                "sha256": "abc",
                "mime_type": "application/octet-stream",
                "storage": "s3",
                "summary": "外部数据集引用",
            },
        )
    )
    assert artifact["uri"] == "s3://bucket/dataset.parquet"
    assert artifact["storage"] == "s3"


def test_artifacts_can_be_listed_globally_for_audit():
    session = _data(
        client.post(
            "/api/v1/research/sessions",
            json={"title": "artifact audit", "information_gain": "global artifact index"},
        )
    )
    artifact = _data(
        client.post(
            f"/api/v1/research/sessions/{session['id']}/artifacts",
            json={
                "artifact_type": "benchmark_result",
                "title": "global artifact reference",
                "uri": "s3://bucket/global-result.json",
                "summary": "全局成果引用审计",
            },
        )
    )
    listed = _data(client.get("/api/v1/artifacts?q=global-result&limit=10"))

    assert listed["total"] >= 1
    assert listed["limit"] == 10
    assert any(item["id"] == artifact["id"] for item in listed["items"])


def test_artifact_audit_reports_reference_gaps_without_reading_external_storage():
    session = _data(
        client.post(
            "/api/v1/research/sessions",
            json={"title": "artifact audit gaps", "information_gain": "artifact integrity"},
        )
    )
    incomplete = _data(
        client.post(
            f"/api/v1/research/sessions/{session['id']}/artifacts",
            json={
                "artifact_type": "benchmark_result",
                "title": "missing integrity metadata",
                "summary": "",
            },
        )
    )
    complete = _data(
        client.post(
            f"/api/v1/research/sessions/{session['id']}/artifacts",
            json={
                "artifact_type": "dataset_ref",
                "title": "complete artifact reference",
                "uri": "s3://bucket/result.parquet",
                "sha256": "f" * 64,
                "mime_type": "application/octet-stream",
                "size_bytes": 2048,
                "storage": "s3",
                "summary": "外部结果引用，包含完整完整性元数据。",
            },
        )
    )

    audit = _data(client.get(f"/api/v1/artifacts/audit?session_id={session['id']}"))

    assert audit["state"] == "blocked"
    assert audit["total"] == 2
    assert audit["issue_counts"]["missing_uri"] == 1
    assert audit["issue_counts"]["missing_hash"] == 1
    assert audit["issue_counts"]["missing_size"] == 1
    assert audit["issue_counts"]["missing_summary"] == 1
    assert incomplete["id"] in audit["artifact_ids_with_issues"]
    assert complete["id"] not in audit["artifact_ids_with_issues"]
    incomplete_report = next(item for item in audit["items"] if item["artifact_id"] == incomplete["id"])
    assert incomplete_report["state"] == "blocked"
    assert any(issue["code"] == "missing_uri" for issue in incomplete_report["issues"])
    assert all(issue["safety"] == "metadata_only_no_external_read" for issue in incomplete_report["issues"])
    assert any(
        action["endpoint"] == "POST /api/v1/research/sessions/{session_id}/artifacts"
        for action in audit["recommended_next_actions"]
    )


def test_research_events_and_experiments_can_be_listed_globally_for_audit():
    session = _data(
        client.post(
            "/api/v1/research/sessions",
            json={"title": "global audit session", "information_gain": "recover process history"},
        )
    )
    event = _data(
        client.post(
            f"/api/v1/research/sessions/{session['id']}/events",
            json={
                "event_type": "blocker",
                "title": "global blocker event",
                "payload": {"summary": "dataset shard unavailable"},
            },
        )
    )
    experiment = _data(
        client.post(
            f"/api/v1/research/sessions/{session['id']}/experiments",
            json={
                "hypothesis": "global experiment recall improves",
                "expected_effect": "recall improves",
                "acceptance_criteria": {"recall_delta_gt": 0.05},
                "rejection_criteria": {"missing_dataset": True},
            },
        )
    )
    patched = _data(
        client.patch(
            f"/api/v1/research/sessions/{session['id']}/experiments/{experiment['id']}",
            json={"status": "degraded", "result_summary": "global experiment degraded by missing shard"},
        )
    )

    events = _data(client.get("/api/v1/research/events?q=global blocker&limit=10"))
    experiments = _data(client.get("/api/v1/research/experiments?status=degraded&q=global experiment&limit=10"))

    assert any(item["id"] == event["id"] for item in events["items"])
    assert any(item["id"] == patched["id"] for item in experiments["items"])
    assert all(item["status"] == "degraded" for item in experiments["items"])


def test_research_context_pack_recovers_topic_state_and_next_actions():
    source = _data(
        client.post(
            "/api/v1/sources",
            json={"kind": "paper", "title": "回放论文", "summary": "回放提升延迟回忆的相关资料"},
        )
    )
    insight = _data(
        client.post(
            "/api/v1/insights",
            json={
                "title": "回放可能提升长期记忆",
                "body": "延迟回忆需要跨轮次恢复上下文。",
                "source_refs": [{"type": "source", "id": source["id"]}],
            },
        )
    )
    hypothesis = _data(
        client.post(
            "/api/v1/hypotheses",
            json={
                "title": "回放提升延迟回忆",
                "hypothesis": "回放提升延迟回忆",
                "expected_effect": "recall improves",
                "insight_refs": [insight["id"]],
            },
        )
    )
    session = _data(
        client.post(
            "/api/v1/research/sessions",
            json={"title": "回放上下文恢复", "information_gain": "恢复已有证据和阻塞"},
        )
    )
    event = _data(
        client.post(
            f"/api/v1/research/sessions/{session['id']}/events",
            json={
                "event_type": "blocker",
                "title": "回放数据集缺分片",
                "payload": {"summary": "缺少一个 delayed recall shard"},
            },
        )
    )
    experiment = _data(
        client.post(
            f"/api/v1/research/sessions/{session['id']}/experiments",
            json={"hypothesis": "回放提升延迟回忆", "expected_effect": "recall improves"},
        )
    )
    patched = _data(
        client.patch(
            f"/api/v1/research/sessions/{session['id']}/experiments/{experiment['id']}",
            json={"status": "degraded", "result_summary": "缺少数据分片，结果只能作为降级证据"},
        )
    )
    artifact = _data(
        client.post(
            f"/api/v1/research/sessions/{session['id']}/artifacts",
            json={
                "artifact_type": "benchmark_result",
                "title": "回放评测结果",
                "summary": "回放评测降级结果引用",
                "uri": "s3://bucket/replay-result.json",
            },
        )
    )
    evidence = _data(
        client.post(
            "/api/v1/evidence-records",
            json={
                "claim": "回放提升延迟回忆",
                "subject": {"type": "hypothesis", "id": hypothesis["id"]},
                "stance": "supports",
                "evidence_kind": "artifact",
                "summary": "已有支持证据，但尚未复现。",
                "evidence_refs": [{"type": "artifact", "id": artifact["id"]}],
                "quality": {"confidence": "medium"},
            },
        )
    )

    context = _data(
        client.get(
            "/api/v1/research/context?query=回放&claim=回放提升延迟回忆&limit=5"
        )
    )

    assert context["query"] == "回放"
    assert context["claim"] == "回放提升延迟回忆"
    assert context["counts"]["sources"] == 1
    assert context["counts"]["insights"] == 1
    assert context["counts"]["hypotheses"] == 1
    assert context["counts"]["sessions"] == 1
    assert context["counts"]["experiments"] == 1
    assert context["counts"]["artifacts"] == 1
    assert context["counts"]["evidence_records"] == 1
    assert context["sections"]["sources"][0]["id"] == source["id"]
    assert context["sections"]["experiments"][0]["id"] == patched["id"]
    assert context["evidence_summary"]["state"] == "needs_replication"
    assert context["evidence_summary"]["evidence_ids"] == [evidence["id"]]
    assert any(flag["id"] == event["id"] and flag["kind"] == "blocker" for flag in context["risk_flags"])
    assert any(flag["id"] == patched["id"] and flag["status"] == "degraded" for flag in context["risk_flags"])
    assert any(action["endpoint"] == "POST /api/v1/research/protocols" for action in context["recommended_next_actions"])


def test_research_rounds_track_worktree_commits_and_experiment_refs():
    session = _data(
        client.post(
            "/api/v1/research/sessions",
            json={"title": "回放方案轮次", "information_gain": "记录每轮方案实现与实验"},
        )
    )
    experiment = _data(
        client.post(
            f"/api/v1/research/sessions/{session['id']}/experiments",
            json={
                "hypothesis": "回放提升延迟回忆",
                "expected_effect": "recall improves",
                "status": "running",
            },
        )
    )
    artifact = _data(
        client.post(
            f"/api/v1/research/sessions/{session['id']}/artifacts",
            json={
                "artifact_type": "code_patch",
                "title": "回放方案实现 diff",
                "summary": "外部 Runtime 在独立 worktree 中实现方案。",
                "uri": "git://repo/commit/abc123",
            },
        )
    )
    evidence = _data(
        client.post(
            "/api/v1/evidence-records",
            json={
                "claim": "回放提升延迟回忆",
                "stance": "supports",
                "evidence_kind": "experiment",
                "summary": "轮次实验形成支持证据。",
                "evidence_refs": [{"type": "experiment", "id": experiment["id"]}],
            },
        )
    )

    response = client.post(
        "/api/v1/research/rounds",
        json={
            "title": "空完成轮次",
            "proposal": "不应允许没有任何追踪引用的完成状态。",
            "status": "completed",
        },
    )
    assert response.status_code == 422

    round_record = _data(
        client.post(
            "/api/v1/research/rounds",
            json={
                "title": "回放方案 A",
                "session_id": session["id"],
                "proposal": "在独立 worktree 中实现回放机制，再回填实验记录。",
                "worktree": {
                    "path": "../worktrees/replay-a",
                    "branch": "research/replay-a",
                    "base_ref": "main",
                },
                "status": "running",
                "runtime": {"name": "external-runtime"},
            },
        )
    )
    assert round_record["status"] == "running"
    assert round_record["worktree"]["branch"] == "research/replay-a"

    completed = _data(
        client.patch(
            f"/api/v1/research/rounds/{round_record['id']}",
            json={
                "status": "completed",
                "implementation_refs": [
                    {"type": "commit", "sha": "abc123", "branch": "research/replay-a"}
                ],
                "experiment_refs": [{"type": "experiment", "id": experiment["id"]}],
                "artifact_refs": [{"type": "artifact", "id": artifact["id"]}],
                "evidence_refs": [{"type": "evidence_record", "id": evidence["id"]}],
                "retrospective": {"next": "登记复现实验轮次"},
            },
        )
    )
    assert completed["status"] == "completed"
    assert completed["implementation_refs"][0]["sha"] == "abc123"
    assert completed["experiment_refs"][0]["id"] == experiment["id"]

    listed = _data(client.get("/api/v1/research/rounds?q=回放方案&status=completed&limit=10"))
    assert listed["total"] == 1
    assert listed["items"][0]["id"] == completed["id"]


def test_research_round_detail_resolves_trace_refs_without_graph():
    session = _data(
        client.post(
            "/api/v1/research/sessions",
            json={"title": "轮次追踪实验", "information_gain": "验证每轮引用恢复"},
        )
    )
    experiment = _data(
        client.post(
            f"/api/v1/research/sessions/{session['id']}/experiments",
            json={"hypothesis": "隔离 worktree 降低回归风险", "expected_effect": "regression risk down"},
        )
    )
    artifact = _data(
        client.post(
            f"/api/v1/research/sessions/{session['id']}/artifacts",
            json={
                "artifact_type": "benchmark_result",
                "title": "轮次追踪结果",
                "uri": "s3://bucket/round-trace.json",
                "summary": "外部 Runtime 产出的实验结果引用",
            },
        )
    )
    evidence = _data(
        client.post(
            "/api/v1/evidence-records",
            json={
                "claim": "隔离 worktree 降低回归风险",
                "stance": "supports",
                "evidence_kind": "artifact",
                "evidence_refs": [{"type": "artifact", "id": artifact["id"]}],
                "quality": {"confidence": "medium"},
            },
        )
    )
    decision = _data(
        client.post(
            "/api/v1/decisions",
            json={
                "subject": {"type": "research_round", "id": "round_pending"},
                "decision": "continue",
                "rationale": "证据足够进入下一轮复现。",
                "evidence_refs": [{"type": "evidence_record", "id": evidence["id"]}],
            },
        )
    )
    round_record = _data(
        client.post(
            "/api/v1/research/rounds",
            json={
                "title": "追踪方案 A",
                "session_id": session["id"],
                "proposal": "用独立 worktree 验证方案 A。",
                "worktree": {"path": "../worktrees/trace-a", "branch": "research/trace-a"},
                "status": "completed",
                "implementation_refs": [{"type": "commit", "sha": "abc123", "branch": "research/trace-a"}],
                "experiment_refs": [{"type": "experiment", "id": experiment["id"]}],
                "artifact_refs": [
                    {"type": "artifact", "id": artifact["id"]},
                    {"type": "artifact", "id": "artifact_missing"},
                ],
                "evidence_refs": [{"type": "evidence_record", "id": evidence["id"]}],
                "decision_refs": [{"type": "decision", "id": decision["id"]}],
            },
        )
    )

    detail = client.get(f"/api/v1/research/rounds/{round_record['id']}")
    assert detail.status_code == 200
    payload = detail.json()
    data = payload["data"]

    assert data["round"]["id"] == round_record["id"]
    assert data["session"]["id"] == session["id"]
    assert data["trace"]["implementation_refs"][0]["sha"] == "abc123"
    assert data["trace"]["experiments"][0]["id"] == experiment["id"]
    assert data["trace"]["artifacts"][0]["id"] == artifact["id"]
    assert data["trace"]["evidence_records"][0]["id"] == evidence["id"]
    assert data["trace"]["decisions"][0]["id"] == decision["id"]
    assert data["trace"]["unresolved_refs"] == [
        {
            "field": "artifact_refs",
            "type": "artifact",
            "id": "artifact_missing",
            "reason": "record_not_found",
        }
    ]
    assert payload["warnings"] == ["unresolved round refs: 1"]
    assert data["safety"] == "read_only_round_trace_no_execution_no_graph"
    assert any(action["action"] == "resolve_missing_round_refs" for action in data["recommended_next_actions"])


def test_research_readiness_check_blocks_on_missing_trace_and_evidence():
    round_record = _data(
        client.post(
            "/api/v1/research/rounds",
            json={
                "title": "就绪检查方案",
                "proposal": "验证平台能在执行前指出缺口。",
                "status": "running",
                "worktree": {"branch": "research/readiness"},
                "artifact_refs": [{"type": "artifact", "id": "artifact_missing"}],
            },
        )
    )

    readiness = _data(
        client.get(
            f"/api/v1/research/readiness?query=就绪检查&claim=就绪检查提升实验质量&round_id={round_record['id']}&stage=before_decision"
        )
    )

    assert readiness["state"] == "blocked"
    check_statuses = {check["id"]: check["status"] for check in readiness["checks"]}
    assert check_statuses["round_trace_refs"] == "fail"
    assert check_statuses["evidence_summary"] == "fail"
    assert readiness["round_trace"]["trace"]["unresolved_refs"] == [
        {
            "field": "artifact_refs",
            "type": "artifact",
            "id": "artifact_missing",
            "reason": "record_not_found",
        }
    ]
    assert readiness["warnings"] == ["unresolved round refs: 1"]
    assert readiness["safety"] == "read_only_readiness_check_no_execution"
    assert any(action["action"] == "resolve_missing_round_refs" for action in readiness["recommended_next_actions"])
    assert any(action["endpoint"] == "POST /api/v1/evidence-records" for action in readiness["recommended_next_actions"])


def test_research_audit_export_bundle_recovers_trace_and_quality_gates():
    session = _data(
        client.post(
            "/api/v1/research/sessions",
            json={"title": "审计导出 session", "information_gain": "导出审计包用于交接"},
        )
    )
    event = _data(
        client.post(
            f"/api/v1/research/sessions/{session['id']}/events",
            json={
                "event_type": "observation",
                "title": "审计导出观察",
                "payload": {"summary": "导出包应包含过程事件"},
            },
        )
    )
    experiment = _data(
        client.post(
            f"/api/v1/research/sessions/{session['id']}/experiments",
            json={"hypothesis": "审计导出提升交接质量", "expected_effect": "handoff improves"},
        )
    )
    artifact = _data(
        client.post(
            f"/api/v1/research/sessions/{session['id']}/artifacts",
            json={
                "artifact_type": "benchmark_result",
                "title": "审计导出结果",
                "uri": "s3://bucket/audit-export.json",
                "sha256": "a" * 64,
                "mime_type": "application/json",
                "size_bytes": 1024,
                "storage": "s3",
                "summary": "审计导出结果引用完整。",
            },
        )
    )
    evidence = _data(
        client.post(
            "/api/v1/evidence-records",
            json={
                "claim": "审计导出提升交接质量",
                "subject": {"type": "experiment", "id": experiment["id"]},
                "stance": "supports",
                "evidence_kind": "artifact",
                "summary": "审计导出包覆盖上下文、轮次和质量门。",
                "evidence_refs": [{"type": "artifact", "id": artifact["id"]}],
                "quality": {"confidence": "high"},
                "limitations": ["仍需外部 Runtime 验证 artifact URI 可访问"],
            },
        )
    )
    review = _data(
        client.post(
            "/api/v1/reviews",
            json={
                "subject": {"type": "evidence_record", "id": evidence["id"]},
                "reviewer": {"kind": "critic", "id": "audit-export-reviewer"},
                "verdict": "completed",
                "score": 91,
                "comments": "审计导出证据链完整。",
                "evidence_refs": [{"type": "evidence_record", "id": evidence["id"]}],
            },
        )
    )
    decision = _data(
        client.post(
            "/api/v1/decisions",
            json={
                "subject": {"type": "evidence_record", "id": evidence["id"]},
                "decision": "accept",
                "rationale": "证据和审查都可追溯。",
                "evidence_refs": [{"type": "evidence_record", "id": evidence["id"]}, {"type": "review", "id": review["id"]}],
            },
        )
    )
    round_record = _data(
        client.post(
            "/api/v1/research/rounds",
            json={
                "title": "审计导出轮次",
                "session_id": session["id"],
                "proposal": "导出一个可交接的只读研究审计包。",
                "status": "completed",
                "worktree": {"branch": "research/audit-export"},
                "experiment_refs": [{"type": "experiment", "id": experiment["id"]}],
                "artifact_refs": [{"type": "artifact", "id": artifact["id"]}],
                "evidence_refs": [{"type": "evidence_record", "id": evidence["id"]}],
                "decision_refs": [{"type": "decision", "id": decision["id"]}],
            },
        )
    )

    export = _data(
        client.get(
            f"/api/v1/research/audit/export?query=审计导出&claim=审计导出提升交接质量&session_id={session['id']}&round_id={round_record['id']}&limit=20"
        )
    )

    assert export["safety"] == "read_only_audit_export_no_execution_no_external_read"
    assert export["manifest"]["schema"] == "autoresearch.audit_bundle.v1"
    assert export["filters"]["session_id"] == session["id"]
    assert export["filters"]["round_id"] == round_record["id"]
    assert export["context"]["counts"]["events"] == 1
    assert export["session_ledger"]["session"]["id"] == session["id"]
    assert export["session_ledger"]["events"][0]["id"] == event["id"]
    assert export["round_trace"]["trace"]["artifacts"][0]["id"] == artifact["id"]
    assert export["round_trace"]["trace"]["evidence_records"][0]["id"] == evidence["id"]
    assert export["round_trace"]["trace"]["decisions"][0]["id"] == decision["id"]
    assert export["artifact_audit"]["state"] == "ready"
    assert export["review_audit"]["state"] == "ready"
    assert export["integrity"]["external_reads"] is False
    assert export["integrity"]["included_artifact_refs"] == [artifact["id"]]
    assert export["reproducibility"]["schema"] == "autoresearch.reproducibility.v1"
    assert export["reproducibility"]["state"] == "degraded"
    assert export["reproducibility"]["external_artifacts"][0]["id"] == artifact["id"]
    assert export["reproducibility"]["external_artifacts"][0]["uri"] == "s3://bucket/audit-export.json"
    assert export["reproducibility"]["external_artifacts"][0]["requires_external_verification"] is True
    checklist = {item["id"]: item for item in export["reproducibility"]["checklist"]}
    assert checklist["session_ledger"]["status"] == "pass"
    assert checklist["round_trace"]["status"] == "pass"
    assert checklist["artifact_metadata"]["status"] == "pass"
    assert checklist["review_gate"]["status"] == "pass"
    assert checklist["evidence_summary"]["status"] == "warn"
    assert any("外部 Runtime" in step for step in export["reproducibility"]["handoff_steps"])
    assert "/api/v1/graph" not in json.dumps(export, ensure_ascii=False).lower()


def test_runtime_event_is_generic_and_has_no_scenario_fields():
    session = _data(
        client.post(
            "/api/v1/research/sessions",
            json={"title": "generic event", "information_gain": "event test"},
        )
    )
    event = _data(
        client.post(
            f"/api/v1/research/sessions/{session['id']}/events",
            json={
                "event_type": "runtime_event",
                "title": "外部输入摘要",
                "payload": {
                    "summary": "外部 Runtime 产生了一条与研究相关的输入摘要",
                    "artifact_refs": [{"type": "artifact", "uri": "s3://bucket/input.jsonl"}],
                },
            },
        )
    )
    assert event["event_type"] == "runtime_event"
    assert event["payload"]["artifact_refs"][0]["uri"] == "s3://bucket/input.jsonl"


def test_experience_curation_update_and_supersede_existing_records():
    session = _data(
        client.post(
            "/api/v1/research/sessions",
            json={"title": "经验维护来源 session", "information_gain": "验证经验来源可解析"},
        )
    )
    review = _data(
        client.post(
            "/api/v1/reviews",
            json={
                "subject": {"type": "session", "id": session["id"]},
                "reviewer": {"kind": "critic", "id": "experience-test-reviewer"},
                "verdict": "completed",
                "comments": "该经验来源有明确 session 记录。",
                "evidence_refs": [{"type": "session", "id": session["id"]}],
            },
        )
    )
    benchmark = _data(
        client.post("/api/v1/benchmarks", json={"name": "经验维护评测", "metric_schema": {"quality": "number"}})
    )
    run = _data(
        client.post(
            "/api/v1/benchmark-runs",
            json={"benchmark_id": benchmark["id"], "status": "running"},
        )
    )
    created = _data(
        client.post(
            "/api/v1/experiences/curation/apply",
            json={
                "runtime": {"name": "tester", "operator": "human"},
                "experience": {"title": "旧经验", "problem": "旧描述", "topics": ["agent-memory"]},
                "source_refs": [{"type": "session", "id": session["id"]}],
            },
        )
    )["experience"]

    updated = _data(
        client.post(
            "/api/v1/experiences/curation/apply",
            json={
                "action": "update",
                "runtime": {"name": "tester", "operator": "human"},
                "experience": {
                    "id": created["id"],
                    "title": "新经验",
                    "problem": "新描述",
                    "topics": ["agent-memory"],
                },
                "source_refs": [{"type": "review", "id": review["id"]}],
            },
        )
    )["experience"]
    assert updated["id"] == created["id"]
    assert updated["title"] == "新经验"

    successor = _data(
        client.post(
            "/api/v1/experiences/curation/apply",
            json={
                "action": "supersede",
                "runtime": {"name": "tester", "operator": "human"},
                "experience": {
                    "supersedes": created["id"],
                    "title": "替代经验",
                    "problem": "更强证据",
                    "topics": ["agent-memory"],
                },
                "source_refs": [{"type": "benchmark_run", "id": run["id"]}],
            },
        )
    )["experience"]
    old = _data(client.get(f"/api/v1/experiences/{created['id']}"))
    assert old["status"] == "superseded"
    assert successor["supersedes"] == created["id"]


def test_experience_curation_apply_requires_source_refs():
    preview = _data(
        client.post(
            "/api/v1/experiences/curation/preview",
            json={
                "runtime": {"name": "tester", "operator": "human"},
                "experience": {"title": "缺少证据", "problem": "没有来源"},
                "source_refs": [],
            },
        )
    )
    assert preview["accepted"] is False
    assert "source_refs is required for durable experience curation" in preview["warnings"]

    response = client.post(
        "/api/v1/experiences/curation/apply",
        json={
            "runtime": {"name": "tester", "operator": "human"},
            "experience": {"title": "缺少证据", "problem": "没有来源"},
            "source_refs": [],
        },
    )
    assert response.status_code == 422


def test_experience_curation_preview_resolves_source_refs_and_governance_gaps():
    evidence = _data(
        client.post(
            "/api/v1/evidence-records",
            json={
                "claim": "经验治理预检需要可追溯证据",
                "subject": {"type": "hypothesis", "id": "hypothesis_curation_governance"},
                "stance": "supports",
                "evidence_kind": "artifact",
                "summary": "来源解析可以阻止无证据经验进入长期记忆。",
                "evidence_refs": [{"type": "artifact", "id": "artifact_curation"}],
                "quality": {"confidence": "high"},
            },
        )
    )
    decision = _data(
        client.post(
            "/api/v1/decisions",
            json={
                "subject": {"type": "experience", "id": "experience_candidate"},
                "decision": "accept",
                "rationale": "证据链完整，可以沉淀为候选经验。",
                "evidence_refs": [{"type": "evidence_record", "id": evidence["id"]}],
            },
        )
    )

    blocked = _data(
        client.post(
            "/api/v1/experiences/curation/preview",
            json={
                "runtime": {"name": "tester", "operator": "external-runtime"},
                "experience": {"title": "经验治理预检", "problem": "来源引用需要先解析"},
                "source_refs": [
                    {"type": "evidence_record", "id": evidence["id"]},
                    {"type": "decision", "id": decision["id"]},
                    {"type": "artifact", "id": "artifact_missing"},
                ],
            },
        )
    )

    assert blocked["accepted"] is False
    assert blocked["safety"] == "read_only_curation_preview_no_auto_extraction"
    assert blocked["source_trace"]["coverage"]["evidence_record"] == 1
    assert blocked["source_trace"]["coverage"]["decision"] == 1
    assert blocked["source_trace"]["resolved"][0]["id"] == evidence["id"]
    assert blocked["source_trace"]["unresolved"] == [
        {"type": "artifact", "id": "artifact_missing", "reason": "record_not_found"}
    ]
    assert any(gap["code"] == "unresolved_source_refs" for gap in blocked["governance_gaps"])
    assert any(
        action["endpoint"] == "POST /api/v1/experiences/curation/preview"
        for action in blocked["recommended_next_actions"]
    )
    response = client.post(
        "/api/v1/experiences/curation/apply",
        json={
            "runtime": {"name": "tester", "operator": "external-runtime"},
            "experience": {"title": "经验治理预检", "problem": "不能绕过阻塞来源"},
            "source_refs": [{"type": "artifact", "id": "artifact_missing"}],
        },
    )
    assert response.status_code == 422
    assert "unresolved source_refs" in response.text

    accepted = _data(
        client.post(
            "/api/v1/experiences/curation/preview",
            json={
                "runtime": {"name": "tester", "operator": "external-runtime"},
                "experience": {"title": "经验治理预检", "problem": "来源引用需要先解析"},
                "source_refs": [
                    {"type": "evidence_record", "id": evidence["id"]},
                    {"type": "decision", "id": decision["id"]},
                ],
            },
        )
    )

    assert accepted["accepted"] is True
    assert accepted["governance_gaps"] == []
    assert accepted["source_trace"]["unresolved"] == []
    assert any(
        action["endpoint"] == "POST /api/v1/experiences/curation/apply"
        for action in accepted["recommended_next_actions"]
    )


def test_research_methodology_primitives_link_program_question_method_and_protocol():
    program = _data(
        client.post(
            "/api/v1/research/programs",
            json={"title": "Agent 记忆研究", "goal": "提升长期任务接续能力"},
        )
    )
    question = _data(
        client.post(
            "/api/v1/research/questions",
            json={
                "program_id": program["id"],
                "question": "延迟回忆是否需要周期性回放",
                "success_criteria": {"recall_delta_gt": 0.05},
            },
        )
    )
    method = _data(
        client.post(
            "/api/v1/research/method-cards",
            json={"name": "延迟回忆评测", "domain": "agent-memory", "failure_modes": ["数据泄漏", "样本过少"]},
        )
    )
    protocol = _data(
        client.post(
            "/api/v1/research/protocols",
            json={
                "question_id": question["id"],
                "method_id": method["id"],
                "one_change": "加入周期性回放",
                "controls": ["无回放基线"],
                "acceptance_criteria": {"recall_delta_gt": 0.05},
                "rejection_criteria": {"latency_delta_gt": 0.2},
            },
        )
    )

    assert protocol["status"] == "planned"
    assert protocol["question_id"] == question["id"]
    assert protocol["method_id"] == method["id"]


def test_research_design_audit_blocks_incomplete_question_hypothesis_and_protocol():
    incomplete_question = _data(
        client.post(
            "/api/v1/research/questions",
            json={"question": "记忆回放是否提升延迟回忆"},
        )
    )
    complete_question = _data(
        client.post(
            "/api/v1/research/questions",
            json={
                "question": "记忆回放是否提升延迟回忆 recall?",
                "rationale": "需要验证长期记忆机制是否可靠。",
                "success_criteria": {"recall_delta_gt": 0.05},
            },
        )
    )
    incomplete_hypothesis = _data(
        client.post(
            "/api/v1/hypotheses",
            json={"title": "记忆回放假设", "hypothesis": "周期性回放提升延迟回忆。"},
        )
    )
    complete_hypothesis = _data(
        client.post(
            "/api/v1/hypotheses",
            json={
                "title": "记忆回放强假设",
                "hypothesis": "周期性回放提升延迟回忆 recall。",
                "expected_effect": "recall@10 提升 5%",
                "acceptance_criteria": {"recall_delta_gt": 0.05},
                "rejection_criteria": {"latency_delta_gt": 0.2},
            },
        )
    )
    method = _data(
        client.post(
            "/api/v1/research/method-cards",
            json={"name": "延迟回忆评测", "required_artifacts": ["benchmark_result", "run_log"]},
        )
    )
    incomplete_protocol = _data(
        client.post(
            "/api/v1/research/protocols",
            json={"question_id": incomplete_question["id"], "hypothesis_id": incomplete_hypothesis["id"], "one_change": "加入回放"},
        )
    )
    complete_protocol = _data(
        client.post(
            "/api/v1/research/protocols",
            json={
                "question_id": complete_question["id"],
                "method_id": method["id"],
                "hypothesis_id": complete_hypothesis["id"],
                "one_change": "加入周期性回放",
                "controls": ["无回放基线"],
                "acceptance_criteria": {"recall_delta_gt": 0.05},
                "rejection_criteria": {"latency_delta_gt": 0.2},
                "artifact_requirements": ["benchmark_result", "run_log"],
            },
        )
    )

    audit = _data(client.get("/api/v1/research/design/audit?q=记忆&limit=20"))

    assert audit["state"] == "blocked"
    assert audit["safety"] == "read_only_design_audit_no_execution"
    assert audit["issue_counts"]["question_missing_success_criteria"] == 1
    assert audit["issue_counts"]["hypothesis_missing_expected_effect"] == 1
    assert audit["issue_counts"]["protocol_missing_controls"] == 1
    assert audit["issue_counts"]["protocol_missing_artifact_requirements"] == 1
    assert incomplete_question["id"] in audit["question_ids_with_issues"]
    assert incomplete_hypothesis["id"] in audit["hypothesis_ids_with_issues"]
    assert incomplete_protocol["id"] in audit["protocol_ids_with_issues"]

    ready_protocol = next(item for item in audit["protocols"] if item["id"] == complete_protocol["id"])
    assert ready_protocol["state"] == "ready"
    assert ready_protocol["issues"] == []
    assert ready_protocol["contract_summary"]["controls"] == 1
    assert ready_protocol["contract_summary"]["artifact_requirements"] == 2
    assert any(action["endpoint"] == "POST /api/v1/research/protocols" for action in audit["recommended_next_actions"])


def test_benchmark_run_requires_provenance_for_completed_scores():
    benchmark = _data(
        client.post("/api/v1/benchmarks", json={"name": "记忆评测", "metric_schema": {"recall": "number"}})
    )
    run = _data(client.post("/api/v1/benchmark-runs", json={"benchmark_id": benchmark["id"], "status": "running"}))
    response = client.patch(
        f"/api/v1/benchmark-runs/{run['id']}",
        json={"status": "completed", "scores": {"recall": 0.7}},
    )
    assert response.status_code == 422

    completed = _data(
        client.patch(
            f"/api/v1/benchmark-runs/{run['id']}",
            json={"status": "completed", "scores": {"recall": 0.7}, "provenance": {"runner": "unit-test"}},
        )
    )
    assert completed["status"] == "completed"


def test_benchmark_suite_audit_requires_external_adapter_contract():
    incomplete = _data(client.post("/api/v1/benchmarks", json={"name": "裸评测"}))
    complete = _data(
        client.post(
            "/api/v1/benchmarks",
            json={
                "name": "记忆回忆评测",
                "domain": "agent-memory",
                "external_runner": {
                    "adapter": "memory-recall-v1",
                    "runtime": "external",
                    "entrypoint": "external-runtime-owned",
                },
                "input_schema": {"dataset_ref": "artifact", "prompt_set": "array"},
                "output_schema": {"scores": "object", "artifact_refs": "array"},
                "metric_schema": {"recall": {"type": "number", "direction": "higher_is_better"}},
                "artifact_requirements": [
                    {"artifact_type": "benchmark_result", "required": True},
                    {"artifact_type": "run_log", "required": True},
                ],
            },
        )
    )

    audit = _data(client.get("/api/v1/benchmarks/audit"))
    assert audit["state"] == "blocked"
    assert audit["safety"] == "registry_only_no_benchmark_execution"
    assert audit["issue_counts"]["missing_external_runner"] == 1
    assert audit["issue_counts"]["missing_metric_schema"] == 1
    assert audit["issue_counts"]["missing_input_contract"] == 1
    assert audit["issue_counts"]["missing_output_contract"] == 1
    assert audit["issue_counts"]["missing_artifact_requirements"] == 1
    assert incomplete["id"] in audit["benchmark_ids_with_issues"]

    complete_item = next(item for item in audit["items"] if item["id"] == complete["id"])
    assert complete_item["state"] == "ready"
    assert complete_item["issues"] == []
    assert complete_item["contract_summary"]["external_runner"] == "memory-recall-v1"
    assert complete_item["contract_summary"]["metric_keys"] == ["recall"]
    assert complete_item["contract_summary"]["artifact_requirement_count"] == 2


def test_benchmark_run_comparison_summarizes_scores_and_quality_gaps():
    benchmark = _data(
        client.post(
            "/api/v1/benchmarks",
            json={
                "name": "记忆回忆对比",
                "domain": "agent-memory",
                "metric_schema": {"recall": {"type": "number", "direction": "higher_is_better"}},
                "input_schema": {"dataset_ref": "artifact"},
                "output_schema": {"scores": "object"},
                "artifact_requirements": [{"artifact_type": "benchmark_result", "required": True}],
                "external_runner": {"adapter": "memory-recall-v1"},
            },
        )
    )
    baseline = _data(
        client.post(
            "/api/v1/benchmark-runs",
            json={
                "benchmark_id": benchmark["id"],
                "status": "completed",
                "scores": {"recall": 0.72},
                "artifact_refs": [{"type": "artifact", "id": "artifact_baseline"}],
                "provenance": {"runner": "unit-test"},
            },
        )
    )
    best = _data(
        client.post(
            "/api/v1/benchmark-runs",
            json={
                "benchmark_id": benchmark["id"],
                "status": "completed",
                "scores": {"recall": 0.81},
                "artifact_refs": [{"type": "artifact", "id": "artifact_best"}],
                "provenance": {"runner": "unit-test"},
            },
        )
    )
    degraded = _data(
        client.post(
            "/api/v1/benchmark-runs",
            json={"benchmark_id": benchmark["id"], "status": "degraded", "scores": {"recall": 0.6}},
        )
    )

    comparison = _data(client.get(f"/api/v1/benchmark-runs/compare?benchmark_id={benchmark['id']}&metric=recall"))

    assert comparison["schema"] == "autoresearch.benchmark_run_comparison.v1"
    assert comparison["state"] == "degraded"
    assert comparison["benchmark_id"] == benchmark["id"]
    assert comparison["metric"] == "recall"
    assert comparison["direction"] == "higher_is_better"
    assert comparison["total"] == 3
    assert comparison["status_counts"]["completed"] == 2
    assert comparison["status_counts"]["degraded"] == 1
    assert comparison["best_run"]["run_id"] == best["id"]
    assert comparison["best_run"]["score"] == 0.81
    assert comparison["score_range"] == {"min": 0.6, "max": 0.81, "delta": 0.21}
    assert [item["run_id"] for item in comparison["ranked_runs"][:2]] == [best["id"], baseline["id"]]
    assert degraded["id"] in comparison["run_ids_with_issues"]
    assert comparison["issue_counts"]["missing_artifact_refs"] == 1
    assert comparison["issue_counts"]["missing_runner_provenance"] == 1
    assert any(action["endpoint"] == "POST /api/v1/evidence-records" for action in comparison["recommended_next_actions"])
    assert comparison["safety"] == "read_only_benchmark_comparison_no_execution"

    operation = app.openapi()["paths"]["/api/v1/benchmark-runs/compare"]["get"]
    assert operation["x-capability-group"] == "benchmark_registry"
    assert operation["x-safety-level"] == "read"
    assert "x-agent-guidance" in operation
    assert "best_run" in operation["x-response-contract"]


def test_reviews_can_be_listed_for_audit():
    review = _data(
        client.post(
            "/api/v1/reviews",
            json={
                "subject": {"type": "benchmark_run", "id": "benchrun_demo"},
                "reviewer": {"kind": "human", "id": "tester"},
                "verdict": "completed",
                "comments": "证据可追溯",
            },
        )
    )
    listed = _data(client.get("/api/v1/reviews?q=benchrun_demo"))
    assert listed["total"] >= 1
    assert any(item["id"] == review["id"] for item in listed["items"])


def test_review_audit_blocks_decision_on_missing_evidence_and_reviewer_provenance():
    evidence = _data(
        client.post(
            "/api/v1/evidence-records",
            json={
                "claim": "审查质量门提升决策可靠性",
                "subject": {"type": "hypothesis", "id": "hypothesis_review_gate"},
                "stance": "supports",
                "evidence_kind": "benchmark_run",
                "summary": "评测结果支持启用审查质量门。",
                "evidence_refs": [{"type": "benchmark_run", "id": "benchrun_review_gate"}],
                "quality": {"confidence": "high"},
            },
        )
    )
    incomplete = _data(
        client.post(
            "/api/v1/reviews",
            json={
                "subject": {"type": "evidence_record", "id": evidence["id"]},
                "reviewer": {},
                "verdict": "completed",
                "comments": "",
                "evidence_refs": [],
            },
        )
    )
    complete = _data(
        client.post(
            "/api/v1/reviews",
            json={
                "subject": {"type": "evidence_record", "id": evidence["id"]},
                "reviewer": {"kind": "critic", "id": "auto-critic-review-gate"},
                "verdict": "completed",
                "score": 86,
                "comments": "审查覆盖证据记录、artifact 完整性和复现缺口。",
                "concerns": [{"code": "replication_gap", "severity": "medium"}],
                "evidence_refs": [{"type": "evidence_record", "id": evidence["id"]}],
            },
        )
    )

    audit = _data(client.get(f"/api/v1/reviews/audit?q={evidence['id']}"))

    assert audit["state"] == "blocked"
    assert audit["total"] == 2
    assert audit["issue_counts"]["missing_reviewer"] == 1
    assert audit["issue_counts"]["missing_comments"] == 1
    assert audit["issue_counts"]["missing_evidence_refs"] == 1
    assert audit["issue_counts"]["missing_score_or_concerns"] == 1
    assert incomplete["id"] in audit["review_ids_with_issues"]
    assert complete["id"] not in audit["review_ids_with_issues"]
    incomplete_report = next(item for item in audit["items"] if item["review_id"] == incomplete["id"])
    assert incomplete_report["state"] == "blocked"
    assert any(issue["code"] == "missing_evidence_refs" for issue in incomplete_report["issues"])
    assert any(action["endpoint"] == "POST /api/v1/reviews" for action in audit["recommended_next_actions"])
    assert any(action["endpoint"] == "POST /api/v1/decisions" for action in audit["recommended_next_actions"])


def test_evidence_records_require_references_and_can_be_listed():
    response = client.post(
        "/api/v1/evidence-records",
        json={
            "claim": "回放提升延迟回忆",
            "stance": "supports",
            "evidence_kind": "benchmark_run",
            "evidence_refs": [],
            "quality": {"confidence": "medium"},
        },
    )
    assert response.status_code == 422

    evidence = _data(
        client.post(
            "/api/v1/evidence-records",
            json={
                "claim": "回放提升延迟回忆",
                "subject": {"type": "hypothesis", "id": "hypothesis_demo"},
                "stance": "supports",
                "evidence_kind": "benchmark_run",
                "summary": "延迟回忆 benchmark 支持该假设，但样本量仍需扩大。",
                "evidence_refs": [{"type": "benchmark_run", "id": "benchrun_demo"}],
                "quality": {"confidence": "medium", "sample_size": 120},
                "limitations": ["样本量偏小"],
                "reproducibility": {"status": "needs_replication"},
            },
        )
    )
    listed = _data(client.get("/api/v1/evidence-records?q=延迟回忆&status=completed&limit=10"))
    assert listed["total"] >= 1
    assert listed["limit"] == 10
    assert any(item["id"] == evidence["id"] for item in listed["items"])
    assert all(item["status"] == "completed" for item in listed["items"])


def test_evidence_summary_groups_claim_conflicts_and_next_action():
    empty = _data(client.get("/api/v1/evidence-records/summary?claim=未验证主张"))
    assert empty["claim"] == "未验证主张"
    assert empty["total"] == 0
    assert empty["state"] == "insufficient"
    assert empty["recommended_next_action"] == "create_evidence_record"

    support = _data(
        client.post(
            "/api/v1/evidence-records",
            json={
                "claim": "回放提升延迟回忆",
                "subject": {"type": "hypothesis", "id": "hypothesis_demo"},
                "stance": "supports",
                "evidence_kind": "benchmark_run",
                "summary": "主评测支持回放。",
                "evidence_refs": [{"type": "benchmark_run", "id": "benchrun_support"}],
                "quality": {"confidence": "high"},
                "limitations": ["样本仍需扩大"],
            },
        )
    )
    contradiction = _data(
        client.post(
            "/api/v1/evidence-records",
            json={
                "claim": "回放提升延迟回忆",
                "subject": {"type": "hypothesis", "id": "hypothesis_demo"},
                "stance": "contradicts",
                "evidence_kind": "replication",
                "summary": "复现实验没有观察到提升。",
                "evidence_refs": [{"type": "benchmark_run", "id": "benchrun_contradiction"}],
                "quality": {"confidence": "medium"},
                "limitations": ["复现样本规模较小"],
            },
        )
    )
    _data(
        client.post(
            "/api/v1/evidence-records",
            json={
                "claim": "无关主张",
                "stance": "supports",
                "evidence_kind": "source",
                "summary": "不应进入目标 claim 的聚合。",
                "evidence_refs": [{"type": "source", "id": "source_other"}],
                "quality": {"confidence": "high"},
            },
        )
    )

    summary = _data(client.get("/api/v1/evidence-records/summary?claim=回放提升延迟回忆"))

    assert summary["claim"] == "回放提升延迟回忆"
    assert summary["total"] == 2
    assert summary["stances"]["supports"] == 1
    assert summary["stances"]["contradicts"] == 1
    assert summary["confidence"]["high"] == 1
    assert summary["confidence"]["medium"] == 1
    assert summary["state"] == "contested"
    assert summary["recommended_next_action"] == "investigate_conflict"
    assert {support["id"], contradiction["id"]} == set(summary["evidence_ids"])
    assert "样本仍需扩大" in summary["limitations"]


def test_evidence_summary_returns_quality_gaps_coverage_and_replication_plan():
    evidence = _data(
        client.post(
            "/api/v1/evidence-records",
            json={
                "claim": "记忆压缩提升长期任务恢复",
                "subject": {"type": "hypothesis", "id": "hypothesis_memory_compaction"},
                "session_id": "session_single",
                "stance": "supports",
                "evidence_kind": "benchmark_run",
                "summary": "单次评测支持该主张，但尚未跨 session 复现。",
                "evidence_refs": [{"type": "benchmark_run", "id": "benchrun_single"}],
                "quality": {"confidence": "medium", "sample_size": 24},
                "reproducibility": {"status": "needs_replication"},
            },
        )
    )

    summary = _data(client.get("/api/v1/evidence-records/summary?claim=记忆压缩提升长期任务恢复"))

    assert summary["coverage"]["evidence_kinds"]["benchmark_run"] == 1
    assert summary["coverage"]["evidence_ref_types"]["benchmark_run"] == 1
    assert summary["coverage"]["sessions"] == ["session_single"]
    assert summary["coverage"]["subjects"] == ["hypothesis:hypothesis_memory_compaction"]
    assert any(gap["code"] == "missing_replication" for gap in summary["quality_gaps"])
    assert any(gap["code"] == "single_session_evidence" for gap in summary["quality_gaps"])
    assert any(gap["code"] == "medium_or_low_confidence" and evidence["id"] in gap["evidence_ids"] for gap in summary["quality_gaps"])
    assert summary["replication_plan"][0]["action"] == "register_independent_replication"
    assert summary["replication_plan"][0]["endpoint"] == "POST /api/v1/research/protocols"


def test_decision_records_require_evidence_and_can_be_listed():
    response = client.post(
        "/api/v1/decisions",
        json={
            "subject": {"type": "hypothesis", "id": "hypothesis_demo"},
            "decision": "accept",
            "rationale": "缺少证据的决策不应入库",
            "evidence_refs": [],
        },
    )
    assert response.status_code == 422

    decision = _data(
        client.post(
            "/api/v1/decisions",
            json={
                "subject": {"type": "hypothesis", "id": "hypothesis_demo"},
                "decision": "continue",
                "rationale": "审查通过但还需要复现实验",
                "evidence_refs": [{"type": "review", "id": "review_demo"}],
                "next_steps": ["登记复现实验协议"],
            },
        )
    )
    listed = _data(client.get("/api/v1/decisions?q=复现实验&limit=10"))
    assert listed["total"] >= 1
    assert listed["limit"] == 10
    assert any(item["id"] == decision["id"] for item in listed["items"])


def test_benchmark_and_experience_contracts():
    benchmark = _data(
        client.post(
            "/api/v1/benchmarks",
            json={"name": "Agent memory recall", "domain": "agent-memory", "metric_schema": {"recall": "number"}},
        )
    )
    run = _data(
        client.post(
            "/api/v1/benchmark-runs",
            json={"benchmark_id": benchmark["id"], "status": "running", "runtime": {"name": "external"}},
        )
    )
    completed = _data(
        client.patch(
            f"/api/v1/benchmark-runs/{run['id']}",
            json={"status": "completed", "scores": {"recall": 0.72}, "provenance": {"runner": "unit-test"}},
        )
    )
    assert completed["scores"]["recall"] == 0.72

    preview = client.post(
        "/api/v1/experiences/curation/preview",
        json={
            "runtime": {"name": "external-agent", "operator": "tester"},
            "experience": {"title": "Replay shard must be complete", "problem": "Partial shards degrade recall."},
            "source_refs": [{"type": "benchmark_run", "id": run["id"]}],
        },
    ).json()
    assert preview["data"]["accepted"] is True
    applied = _data(
        client.post(
            "/api/v1/experiences/curation/apply",
            json={
                "runtime": {"name": "external-agent", "operator": "tester"},
                "experience": {
                    "title": "Replay shard must be complete",
                    "problem": "Partial shards degrade recall.",
                    "topics": ["agent-memory"],
                },
                "source_refs": [{"type": "benchmark_run", "id": run["id"]}],
            },
        )
    )
    assert applied["experience"]["status"] == "candidate"
    query = _data(client.post("/api/v1/experiences/query", json={"query": "Replay", "limit": 5}))
    assert query["total"] >= 1

    topic = _data(
        client.put(
            "/api/v1/experience-topics/agent-memory/summary",
            json={
                "title": "Agent memory",
                "summary": "Replay evidence and failure modes.",
                "source_refs": [{"type": "experience", "id": applied["experience"]["id"]}],
                "runtime": {"name": "external-agent", "operator": "tester"},
            },
        )
    )
    assert topic["id"] == "agent-memory"
    topics = _data(client.get("/api/v1/experience-topics"))
    assert any(item["id"] == "agent-memory" for item in topics)


def test_public_contract_excludes_graph_lineage_and_legacy_modules():
    schema = app.openapi()
    schema_text = json.dumps(app.openapi(), ensure_ascii=False)
    forbidden_public_paths = [
        "/api/v1/graph",
        "/api/v1/graph/links",
        "/api/v1/research/lineage",
        "/mcp",
        "/qronos",
        "/trading",
        "/factors",
        "/strategies",
    ]
    for path in forbidden_public_paths:
        assert path not in schema["paths"]

    assert "graph" not in {capability["id"] for capability in schema["x-agent-capabilities"]}
    for methods in schema["paths"].values():
        for method, operation in methods.items():
            if method in {"get", "post", "patch", "put", "delete"}:
                assert operation["x-capability-group"] != "graph"

    forbidden_tables = [
        "graph_nodes",
        "graph_edges",
        "research_workflow_definitions",
        "research_runs",
        "research_steps",
        "research_evaluations",
        "research_reports",
        "research_chunks",
        "rag_evaluations",
    ]
    migration_text = Path("migrations/versions/20260629_0001_initial_autoresearch_schema.py").read_text()
    for table in forbidden_tables:
        assert table not in migration_text
        assert table not in schema_text


def test_repository_demo_store_does_not_advertise_legacy_graph_collections():
    store_path = Path("../data/autoresearch_store.json")
    store_data = json.loads(store_path.read_text(encoding="utf-8"))

    assert "graph_nodes" not in store_data
    assert "graph_edges" not in store_data


def test_json_store_drops_legacy_unknown_collections_on_next_write(tmp_path):
    store_path = tmp_path / "legacy_store.json"
    store_path.write_text(
        json.dumps(
            {
                "sources": [],
                "graph_nodes": [{"id": "legacy_graph_node"}],
                "graph_edges": [{"id": "legacy_graph_edge"}],
            }
        ),
        encoding="utf-8",
    )
    store = JsonResearchStore(store_path)

    store.create_record("sources", "source", {"title": "kept source", "kind": "paper"})

    persisted = json.loads(store_path.read_text(encoding="utf-8"))
    assert "sources" in persisted
    assert "graph_nodes" not in persisted
    assert "graph_edges" not in persisted
    assert set(persisted) == set(main_module.store.health()["collections"])


def test_auto_research_skill_guides_round_trace_recovery_without_graph():
    skill_text = Path("../.agents/skills/auto-research/SKILL.md").read_text()
    session_loop = Path("../.agents/skills/auto-research/examples/session-loop.md").read_text()
    schema = app.openapi()

    assert "GET /api/v1/research/rounds/{round_id}" in skill_text
    assert "GET /api/v1/agent/onboarding" in skill_text
    assert "GET /api/v1/research/readiness" in skill_text
    assert "GET /api/v1/research/method-templates" in skill_text
    assert "追踪包" in skill_text
    assert "就绪检查" in skill_text
    assert "unresolved_refs" in skill_text
    assert "quality_gaps" in skill_text
    assert "replication_plan" in skill_text
    assert "GET /api/v1/artifacts/audit" in skill_text
    assert "GET /api/v1/reviews/audit" in skill_text
    assert "GET /api/v1/research/audit/export" in skill_text
    assert "reproducibility.checklist" in skill_text
    assert "external_artifacts" in skill_text
    assert "handoff_steps" in skill_text
    assert "source_trace" in skill_text
    assert "governance_gaps" in skill_text
    export_contract = schema["paths"]["/api/v1/research/audit/export"]["get"]["x-response-contract"]
    assert "reproducibility" in export_contract
    assert "GET /api/v1/agent/onboarding" in session_loop
    assert "GET /api/v1/research/rounds/{round_id}" in session_loop
    assert "GET /api/v1/research/readiness" in session_loop
    assert "GET /api/v1/research/method-templates" in session_loop
    assert "quality_gaps" in session_loop
    assert "replication_plan" in session_loop
    assert "GET /api/v1/artifacts/audit" in session_loop
    assert "GET /api/v1/reviews/audit" in session_loop
    assert "GET /api/v1/research/audit/export" in session_loop
    assert "governance_gaps" in session_loop
    assert "/api/v1/graph" not in skill_text
    assert "图谱" not in skill_text


def test_auto_research_skill_uses_progressive_capability_references():
    skill_dir = Path("../.agents/skills/auto-research")
    skill_text = (skill_dir / "SKILL.md").read_text()
    reference_names = [
        "bootstrap.md",
        "research-design.md",
        "execution-ledger.md",
        "evidence-review-decision.md",
        "experience-curation.md",
        "safety-boundaries.md",
    ]

    assert len(skill_text.splitlines()) <= 70
    assert "## Capability References" in skill_text
    for reference_name in reference_names:
        reference_path = skill_dir / "references" / reference_name
        assert f"references/{reference_name}" in skill_text
        assert reference_path.exists(), f"missing auto-research reference {reference_name}"

    package_text = "\n".join(
        [
            skill_text,
            *((skill_dir / "references" / name).read_text() for name in reference_names),
            (skill_dir / "examples" / "session-loop.md").read_text(),
            (skill_dir / "examples" / "experience-curation.md").read_text(),
        ]
    )
    for endpoint in [
        "GET /api/v1/system/security",
        "GET /api/v1/agent/onboarding",
        "GET /api/v1/research/method-templates",
        "GET /api/v1/research/design/audit",
        "GET /api/v1/research/rounds/{round_id}",
        "GET /api/v1/artifacts/audit",
        "GET /api/v1/reviews/audit",
        "GET /api/v1/research/audit/export",
        "POST /api/v1/experiences/curation/preview",
        "POST /api/v1/experiences/curation/apply",
    ]:
        assert endpoint in package_text
    assert "OpenAPI" in package_text
    assert "/api/v1/graph" not in package_text
    assert "图谱" not in package_text

"""Public v1 AutoResearch routes."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from autoresearch_platform.core.openapi_docs import AGENT_CAPABILITIES, agent_guidance
from autoresearch_platform.core.config import get_settings
from autoresearch_platform.core.security import security_status
from autoresearch_platform.schemas import (
    ApiEnvelope,
    ArtifactCreate,
    BenchmarkCreate,
    BenchmarkRunCreate,
    BenchmarkRunPatch,
    DecisionCreate,
    EvidenceRecordCreate,
    EventCreate,
    ExperienceCurationRequest,
    ExperienceQuery,
    ExperienceTopicSummaryUpdate,
    ExperimentCreate,
    ExperimentPatch,
    HypothesisCreate,
    IdeaCreate,
    InsightCreate,
    IntakeCreate,
    MethodCardCreate,
    PlanCreate,
    ProtocolCreate,
    ResearchRoundCreate,
    ResearchRoundPatch,
    ResearchProgramCreate,
    ResearchQuestionCreate,
    ResultCreate,
    ReviewCreate,
    SessionClose,
    SessionCreate,
    SourceCreate,
)
from autoresearch_platform.services import ResearchStore
from autoresearch_platform.services.store import COLLECTION_TABLES


router = APIRouter()

FORBIDDEN_ARTIFACT_PAYLOAD_KEYS = {
    "raw_content",
    "full_text",
    "binary",
    "base64",
    "audio",
    "video",
    "checkpoint",
}
MAX_ARTIFACT_PAYLOAD_BYTES = 8192
EVIDENCE_STANCES = [
    "supports",
    "contradicts",
    "mixed",
    "inconclusive",
    "replicates",
    "fails_to_replicate",
]
RESEARCH_CONTEXT_COLLECTIONS = {
    "sources": "sources",
    "insights": "insights",
    "hypotheses": "hypotheses",
    "research_questions": "research_questions",
    "method_cards": "method_cards",
    "protocols": "protocols",
    "intake_items": "intake_items",
    "sessions": "sessions",
    "research_rounds": "research_rounds",
    "events": "events",
    "experiments": "experiments",
    "artifacts": "artifacts",
    "benchmark_runs": "benchmark_runs",
    "evidence_records": "evidence_records",
    "reviews": "reviews",
    "decisions": "decisions",
    "experiences": "experiences",
}
RISK_STATUSES = {"blocked", "degraded", "failed"}
ROUND_TRACE_REF_FIELDS = [
    "implementation_refs",
    "experiment_refs",
    "artifact_refs",
    "evidence_refs",
    "decision_refs",
]
ROUND_TRACE_REF_COLLECTIONS = {
    "experiment_refs": ("experiment", "experiments", "experiments"),
    "artifact_refs": ("artifact", "artifacts", "artifacts"),
    "benchmark_refs": ("benchmark_run", "benchmark_runs", "benchmark_runs"),
    "evidence_refs": ("evidence_record", "evidence_records", "evidence_records"),
    "decision_refs": ("decision", "decisions", "decisions"),
}
AUTO_RESEARCH_SKILL_LOAD_ORDER = [
    "references/bootstrap.md",
    "references/research-design.md",
    "references/execution-ledger.md",
    "references/evidence-review-decision.md",
    "references/experience-curation.md",
    "references/safety-boundaries.md",
]
RESEARCH_METHOD_TEMPLATES = [
    {
        "id": "literature_synthesis",
        "title": "文献综合",
        "when_to_use": "需要从论文、报告、代码仓库或外部资料中提炼研究问题、机制解释、缺口和可验证假设。",
        "design_questions": [
            "当前 claim 的主要证据类型是什么？",
            "有哪些互相冲突或尚未复现的结论？",
            "哪些 insight 可以转成可证伪假设？",
        ],
        "required_records": ["source", "insight", "hypothesis"],
        "protocol_defaults": {
            "one_change": "只改变综述范围或纳入标准，不执行实验",
            "controls": ["纳入标准", "排除标准"],
            "acceptance_criteria": {"has_traceable_sources": True, "has_testable_hypotheses": True},
            "rejection_criteria": {"untraceable_claims": True},
        },
        "artifact_requirements": ["source_registry", "synthesis_note"],
        "evidence_expectations": ["证据必须引用 source 或 insight", "把不确定结论标为 inconclusive"],
        "review_gates": ["来源覆盖范围", "相互冲突结论", "可证伪性"],
        "next_endpoints": [
            "POST /api/v1/sources",
            "POST /api/v1/insights",
            "POST /api/v1/hypotheses",
            "GET /api/v1/research/design/audit",
        ],
    },
    {
        "id": "reproduction",
        "title": "复现实验",
        "when_to_use": "需要确认论文、benchmark、历史 run 或外部 Runtime 结果是否能在独立环境中复现。",
        "design_questions": [
            "复现目标、版本、数据、随机种子和环境是否固定？",
            "原始 baseline artifact 与复现 artifact 如何对齐？",
            "失败时如何区分实现错误、数据漂移和方法本身不可复现？",
        ],
        "required_records": ["research_question", "method_card", "protocol", "baseline_artifact", "reproduction_artifact"],
        "protocol_defaults": {
            "one_change": "复现目标或环境固定，先不引入新方法变化",
            "controls": ["原始报告指标", "固定数据版本", "固定随机种子"],
            "acceptance_criteria": {"metric_within_tolerance": True, "artifact_hash_recorded": True},
            "rejection_criteria": {"missing_baseline": True, "unresolved_artifact": True},
        },
        "artifact_requirements": ["baseline_artifact", "run_log", "result_artifact", "environment_manifest"],
        "evidence_expectations": ["优先写 replicates 或 fails_to_replicate", "记录复现限制和环境差异"],
        "review_gates": ["artifact hash", "环境清单", "指标容差", "失败归因"],
        "next_endpoints": [
            "POST /api/v1/research/method-cards",
            "POST /api/v1/research/protocols",
            "POST /api/v1/research/rounds",
            "POST /api/v1/evidence-records",
            "GET /api/v1/reviews/audit",
        ],
    },
    {
        "id": "ablation",
        "title": "消融实验",
        "when_to_use": "需要隔离单一机制、模块、prompt、参数、数据处理或 agent skill 对结果的贡献。",
        "design_questions": [
            "本轮唯一变化是什么？",
            "对照组是否保留除了该变化以外的全部条件？",
            "接受与拒绝标准是否能区分真实机制和噪声？",
        ],
        "required_records": ["hypothesis", "research_question", "protocol", "research_round"],
        "protocol_defaults": {
            "one_change": "只改变一个机制或配置",
            "controls": ["当前基线", "无该机制版本"],
            "acceptance_criteria": {"directional_effect_matches_hypothesis": True},
            "rejection_criteria": {"effect_absent_or_opposite": True},
        },
        "artifact_requirements": ["config_diff", "run_log", "result_artifact"],
        "evidence_expectations": ["绑定实验 artifact 与假设", "记录样本量和变异来源"],
        "review_gates": ["唯一变化", "对照完整性", "统计或阈值依据"],
        "next_endpoints": [
            "POST /api/v1/research/protocols",
            "POST /api/v1/research/rounds",
            "GET /api/v1/research/readiness",
            "POST /api/v1/evidence-records",
        ],
    },
    {
        "id": "benchmark_comparison",
        "title": "评测对比",
        "when_to_use": "需要比较模型、agent、方法、数据处理或工具链在固定 benchmark 合同下的表现。",
        "design_questions": [
            "benchmark suite 的输入、输出、指标和 artifact 要求是否固定？",
            "对比对象是否使用相同数据和运行条件？",
            "run 结果是否可追踪到外部适配器和 artifact？",
        ],
        "required_records": ["benchmark_suite", "benchmark_run", "artifact", "evidence_record"],
        "protocol_defaults": {
            "one_change": "只改变被比较对象",
            "controls": ["固定 benchmark suite", "固定数据版本", "固定评分脚本"],
            "acceptance_criteria": {"metric_direction_declared": True, "artifact_refs_present": True},
            "rejection_criteria": {"missing_runner_provenance": True},
        },
        "artifact_requirements": ["benchmark_result", "run_log", "score_report"],
        "evidence_expectations": ["先跑 benchmark audit", "completed run 必须有 artifact_refs 或 provenance.runner"],
        "review_gates": ["suite 合同", "runner provenance", "分数方向", "artifact 完整性"],
        "next_endpoints": [
            "POST /api/v1/benchmarks",
            "GET /api/v1/benchmarks/audit",
            "POST /api/v1/benchmark-runs",
            "GET /api/v1/artifacts/audit",
            "POST /api/v1/evidence-records",
        ],
    },
    {
        "id": "failure_analysis",
        "title": "失败分析",
        "when_to_use": "需要把 failed、blocked 或 degraded 的 run 转成可复用的错误分类、后续实验和长期经验候选。",
        "design_questions": [
            "失败是数据、实现、评测合同、环境还是假设问题？",
            "哪些 artifact 或日志能支持该归因？",
            "下一轮最小修复实验是什么？",
        ],
        "required_records": ["event", "experiment", "artifact", "review", "decision"],
        "protocol_defaults": {
            "one_change": "只验证一个失败原因或修复策略",
            "controls": ["失败 run", "最小修复 run"],
            "acceptance_criteria": {"failure_cause_resolved": True},
            "rejection_criteria": {"failure_recurs": True},
        },
        "artifact_requirements": ["failure_log", "diagnostic_summary", "fix_result"],
        "evidence_expectations": ["用 contradicts 或 inconclusive 记录假设风险", "决策可为 blocked 或 continue"],
        "review_gates": ["失败归因", "证据引用", "下一步是否可执行"],
        "next_endpoints": [
            "POST /api/v1/research/sessions/{session_id}/events",
            "GET /api/v1/research/audit/export",
            "POST /api/v1/reviews",
            "POST /api/v1/decisions",
            "POST /api/v1/experiences/curation/preview",
        ],
    },
]

METHOD_LOOP_STAGES = [
    {
        "id": "idea_pool",
        "label": "Idea Pool",
        "purpose": "论文、repo、数据集、benchmark gap、研究员想法、历史失败和外部观察。",
        "primary_endpoint": "POST /api/v1/ideas",
        "list_endpoint": "GET /api/v1/ideas",
        "backing_collection": "sources",
    },
    {
        "id": "hypothesis",
        "label": "Hypothesis",
        "purpose": "把 idea 收敛成一个可验证假设，并保留来源引用。",
        "primary_endpoint": "POST /api/v1/hypotheses",
        "list_endpoint": "GET /api/v1/hypotheses",
        "backing_collection": "hypotheses",
    },
    {
        "id": "plan",
        "label": "Plan",
        "purpose": "记录唯一变化、验证方式、接受/拒绝标准和结果要求；不是 workflow DAG。",
        "primary_endpoint": "POST /api/v1/plans",
        "list_endpoint": "GET /api/v1/plans",
        "backing_collection": "protocols",
    },
    {
        "id": "experiment",
        "label": "Experiment",
        "purpose": "记录外部 Runtime 的一次执行；平台不执行实验。",
        "primary_endpoint": "POST /api/v1/research/sessions",
        "list_endpoint": "GET /api/v1/research/experiments",
        "backing_collection": "experiments",
    },
    {
        "id": "result",
        "label": "Result",
        "purpose": "登记分数、日志、图表、badcase、commit、报告或论文草稿等外部结果引用。",
        "primary_endpoint": "POST /api/v1/results",
        "list_endpoint": "GET /api/v1/results",
        "backing_collection": "artifacts",
    },
    {
        "id": "review",
        "label": "Review",
        "purpose": "对 result 做解释、复盘、artifact-aware review 或质量缺口审计。",
        "primary_endpoint": "POST /api/v1/reviews",
        "list_endpoint": "GET /api/v1/reviews",
        "backing_collection": "reviews",
    },
    {
        "id": "decision",
        "label": "Decision",
        "purpose": "写入 keep、discard、continue、retry、blocked 或 archived 等迭代判断。",
        "primary_endpoint": "POST /api/v1/decisions",
        "list_endpoint": "GET /api/v1/decisions",
        "backing_collection": "decisions",
    },
    {
        "id": "lesson",
        "label": "Lesson",
        "purpose": "显式沉淀有来源追踪的可复用经验，指导下一轮 hypothesis 或 plan。",
        "primary_endpoint": "POST /api/v1/experiences/curation/preview",
        "list_endpoint": "GET /api/v1/lessons",
        "backing_collection": "experiences",
    },
]


def get_store() -> ResearchStore:
    from autoresearch_platform.main import store

    return store


def envelope(data: Any, warnings: list[str] | None = None) -> ApiEnvelope:
    return ApiEnvelope(data=data, warnings=warnings or [])


def require_record(record: dict[str, Any] | None, record_id: str) -> dict[str, Any]:
    if not record:
        raise HTTPException(status_code=404, detail=f"record not found: {record_id}")
    return record


def query_records(
    store: ResearchStore,
    collection: str,
    *,
    status: str | None,
    q: str,
    limit: int,
    offset: int,
    sort: str,
) -> ApiEnvelope:
    return envelope(
        store.query_records(
            collection,
            status=status,
            q=q,
            limit=limit,
            offset=offset,
            sort=sort,
        )
    )


def attach_loop_metadata(payload: dict[str, Any], stage: str) -> dict[str, Any]:
    metadata = dict(payload.get("metadata") or {})
    metadata.setdefault("loop_stage", stage)
    payload["metadata"] = metadata
    return payload


def _read_schema_contract() -> dict[str, Any]:
    migration_path = Path(__file__).resolve().parents[3] / "migrations" / "versions" / "20260629_0001_initial_autoresearch_schema.py"
    text = migration_path.read_text(encoding="utf-8")
    uses_text_ids = "id TEXT PRIMARY KEY" in text and "id UUID" not in text and "gen_random_uuid" not in text
    missing_collection_tables = [
        table
        for table in COLLECTION_TABLES.values()
        if f'_json_table("{table}"' not in text
    ]
    forbids_legacy_tables = all(
        legacy not in text
        for legacy in [
            "graph_nodes",
            "graph_edges",
            "research_workflow_definitions",
            "research_runs",
            "research_chunks",
            "rag_evaluations",
        ]
    )
    return {
        "migration": str(migration_path.name),
        "uses_platform_text_ids": uses_text_ids,
        "covers_store_collections": not missing_collection_tables,
        "missing_collection_tables": missing_collection_tables,
        "forbids_legacy_tables": forbids_legacy_tables,
        "payload_model": "jsonb_payload_tables",
    }


def build_system_readiness(store: ResearchStore) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    recommended_next_actions: list[dict[str, Any]] = []
    store_health = store.health()
    schema_contract = _read_schema_contract()

    def add_check(
        check_id: str,
        status: str,
        title: str,
        detail: str,
        *,
        action: dict[str, Any] | None = None,
    ) -> None:
        check = {"id": check_id, "status": status, "title": title, "detail": detail}
        if action:
            check["recommended_action"] = action
            recommended_next_actions.append(action)
        checks.append(check)

    add_check(
        "store_access",
        "pass",
        "存储可访问",
        f"当前存储类型={store_health.get('store')}。",
    )

    if store_health.get("store") == "json":
        add_check(
            "durable_store",
            "warn",
            "持久化模式",
            "当前使用本地 JSON 存储，适合开发和演示，不是生产持久化配置。",
            action={
                "endpoint": "docs/architecture/reference.md",
                "reason": "生产部署前启用 PostgreSQL 存储适配器并运行 Alembic 迁移。",
                "priority": "normal",
            },
        )
    elif store_health.get("status") == "adapter_boundary_only":
        add_check(
            "durable_store",
            "fail",
            "持久化模式",
            "PostgreSQL 已配置，但读写适配器尚未启用。",
            action={
                "endpoint": "backend/autoresearch_platform/services/postgres_store.py",
                "reason": "实现并验证 PostgreSQL 存储适配器后再用于生产。",
                "priority": "high",
            },
        )
    else:
        add_check("durable_store", "pass", "持久化模式", "已启用持久化存储。")

    add_check(
        "platform_text_id_contract",
        "pass" if schema_contract["uses_platform_text_ids"] else "fail",
        "平台 ID 合同",
        "PostgreSQL 数据库结构使用平台文本 ID。" if schema_contract["uses_platform_text_ids"] else "PostgreSQL 数据库结构未使用平台文本 ID。",
        action=(
            None
            if schema_contract["uses_platform_text_ids"]
            else {
                "endpoint": "backend/migrations/versions/20260629_0001_initial_autoresearch_schema.py",
                "reason": "迁移必须使用 id TEXT PRIMARY KEY，以保存 source_、session_、artifact_ 等平台 ID。",
                "priority": "high",
            }
        ),
    )
    add_check(
        "schema_collection_coverage",
        "pass" if schema_contract["covers_store_collections"] else "fail",
        "存储表覆盖",
        "PostgreSQL 数据库结构覆盖全部平台 collection。"
        if schema_contract["covers_store_collections"]
        else f"PostgreSQL 数据库结构缺少表: {', '.join(schema_contract['missing_collection_tables'])}。",
        action=(
            None
            if schema_contract["covers_store_collections"]
            else {
                "endpoint": "backend/migrations/versions/20260629_0001_initial_autoresearch_schema.py",
                "reason": "为每个 ResearchStore collection 补齐 PostgreSQL 表，避免外部运行时写入后无法持久化。",
                "priority": "high",
            }
        ),
    )
    add_check(
        "legacy_schema_exclusion",
        "pass" if schema_contract["forbids_legacy_tables"] else "fail",
        "旧模块排除",
        "数据库结构未包含旧关系推断、旧工作流或 RAG 原文表。" if schema_contract["forbids_legacy_tables"] else "数据库结构泄漏旧模块表。",
    )

    if any(check["status"] == "fail" for check in checks):
        state = "blocked"
    elif any(check["status"] == "warn" for check in checks):
        state = "degraded"
    else:
        state = "ready"

    return {
        "state": state,
        "checks": checks,
        "store": store_health,
        "schema_contract": schema_contract,
        "recommended_next_actions": recommended_next_actions,
        "safety": "read_only_deployment_readiness_no_external_access",
    }


def build_agent_onboarding(store: ResearchStore, *, api_prefix: str, api_token: str | None) -> dict[str, Any]:
    readiness = build_system_readiness(store)
    security = security_status(api_prefix, api_token)
    capability_groups = {
        capability["id"]: {
            "name": capability["name"],
            "primary_endpoint": capability["primary_endpoint"],
            "next_endpoints": capability.get("next_endpoints", []),
            "when_to_use": capability.get("when_to_use", ""),
            "safety": capability.get("safety", ""),
        }
        for capability in AGENT_CAPABILITIES
    }
    recommended_first_calls = [
        "GET /api/v1/agent/onboarding",
        "GET /api/v1/method-loop",
        "GET /api/v1/system/security",
        "GET /api/v1/system/readiness",
        "GET /api/v1/capabilities",
        "POST /api/v1/experiences/query",
        "GET /api/v1/research/context?query=...&claim=...",
        "GET /api/v1/research/readiness?query=...&claim=...&round_id=...&stage=before_experiment",
        "GET /api/v1/research/design/audit",
    ]
    return {
        "schema": "autoresearch.agent_onboarding.v1",
        "state": readiness["state"],
        "openapi": f"{api_prefix}/openapi.json",
        "docs": {
            "external_runtime_api": "docs/architecture/external-runtime-api.md",
            "research_methodology": "docs/architecture/research-methodology.md",
            "boundary_rules": "docs/architecture/boundary-rules.md",
        },
        "skill": {
            "name": "auto-research",
            "path": ".agents/skills/auto-research/SKILL.md",
            "load_order": AUTO_RESEARCH_SKILL_LOAD_ORDER,
            "method_source": "Skill references define endpoint composition; OpenAPI verifies route/schema drift.",
        },
        "security": security,
        "readiness": {
            "state": readiness["state"],
            "checks": readiness["checks"],
            "recommended_next_actions": readiness["recommended_next_actions"],
            "safety": readiness["safety"],
        },
        "capability_count": len(AGENT_CAPABILITIES),
        "capability_groups": capability_groups,
        "recommended_first_calls": recommended_first_calls,
        "recommended_next_actions": readiness["recommended_next_actions"],
        "integrity": {
            "external_reads": False,
            "external_writes": False,
            "executes_runtime": False,
            "returns_openapi_body": False,
        },
        "safety": "read_only_onboarding_no_execution_no_external_access",
    }


def _find_forbidden_artifact_key(value: Any) -> str | None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key.lower() in FORBIDDEN_ARTIFACT_PAYLOAD_KEYS:
                return key
            found = _find_forbidden_artifact_key(nested)
            if found:
                return found
    if isinstance(value, list):
        for nested in value:
            found = _find_forbidden_artifact_key(nested)
            if found:
                return found
    return None


def validate_artifact_reference(payload: dict[str, Any]) -> None:
    found = _find_forbidden_artifact_key(payload)
    if found:
        raise HTTPException(
            status_code=422,
            detail=f"artifact content must remain external; forbidden inline payload key: {found}",
        )
    payload_bytes = len(json.dumps(payload.get("payload", {}), ensure_ascii=False).encode("utf-8"))
    if payload_bytes > MAX_ARTIFACT_PAYLOAD_BYTES:
        raise HTTPException(
            status_code=422,
            detail="artifact payload is too large; store content externally and submit URI/hash/MIME metadata",
        )


def build_artifact_issues(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    def add_issue(code: str, severity: str, message: str) -> None:
        issues.append(
            {
                "code": code,
                "severity": severity,
                "message": message,
                "safety": "metadata_only_no_external_read",
            }
        )

    if not str(artifact.get("uri") or "").strip():
        add_issue("missing_uri", "high", "artifact 缺少外部 URI，无法追踪真实结果位置。")
    if not str(artifact.get("sha256") or "").strip():
        add_issue("missing_hash", "high", "artifact 缺少 hash，无法校验外部结果是否变化。")
    if artifact.get("size_bytes") in {None, ""}:
        add_issue("missing_size", "medium", "artifact 缺少 size_bytes，难以判断是否为大型外部对象引用。")
    if not str(artifact.get("summary") or "").strip():
        add_issue("missing_summary", "medium", "artifact 缺少摘要，后续审查难以理解其证据含义。")
    if not str(artifact.get("storage") or "").strip():
        add_issue("missing_storage", "medium", "artifact 缺少 storage，无法判断外部存储边界。")

    found = _find_forbidden_artifact_key(artifact.get("payload") or {})
    if found:
        add_issue("inline_payload_risk", "high", f"artifact payload 包含疑似内联内容字段: {found}。")

    return issues


def build_artifact_audit(records: list[dict[str, Any]], *, q: str, session_id: str | None) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    issue_counts: dict[str, int] = {}
    artifact_ids_with_issues: list[str] = []
    high_issue_count = 0
    medium_issue_count = 0

    for artifact in records:
        issues = build_artifact_issues(artifact)
        for issue in issues:
            code = str(issue["code"])
            issue_counts[code] = issue_counts.get(code, 0) + 1
            if issue["severity"] == "high":
                high_issue_count += 1
            elif issue["severity"] == "medium":
                medium_issue_count += 1
        if issues:
            artifact_ids_with_issues.append(str(artifact.get("id")))

        item_state = "blocked" if any(issue["severity"] == "high" for issue in issues) else "degraded" if issues else "ready"
        items.append(
            {
                "artifact_id": artifact.get("id"),
                "title": artifact.get("title") or artifact.get("artifact_type") or artifact.get("id"),
                "artifact_type": artifact.get("artifact_type"),
                "session_id": artifact.get("session_id"),
                "uri": artifact.get("uri"),
                "storage": artifact.get("storage"),
                "state": item_state,
                "issues": issues,
            }
        )

    if high_issue_count:
        state = "blocked"
    elif medium_issue_count:
        state = "degraded"
    else:
        state = "ready"

    recommended_next_actions: list[dict[str, Any]] = []
    if issue_counts:
        recommended_next_actions.append(
            {
                "endpoint": "POST /api/v1/research/sessions/{session_id}/artifacts",
                "reason": "重新登记包含 URI、hash、MIME、size_bytes、storage 和 summary 的外部 artifact 引用。",
                "priority": "high" if high_issue_count else "normal",
            }
        )
    if issue_counts.get("missing_hash") or issue_counts.get("missing_size"):
        recommended_next_actions.append(
            {
                "endpoint": "POST /api/v1/evidence-records",
                "reason": "补齐 artifact 完整性元数据后，再把它作为 evidence_refs 写入证据记录。",
                "priority": "normal",
            }
        )

    return {
        "state": state,
        "query": q,
        "session_id": session_id,
        "total": len(records),
        "issue_counts": issue_counts,
        "artifact_ids_with_issues": artifact_ids_with_issues,
        "items": items,
        "recommended_next_actions": recommended_next_actions,
        "safety": "metadata_only_no_external_read",
    }


def build_review_issues(review: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    def add_issue(code: str, severity: str, message: str) -> None:
        issues.append({"code": code, "severity": severity, "message": message, "safety": "ledger_only_no_critic_execution"})

    subject = review.get("subject") if isinstance(review.get("subject"), dict) else {}
    if not str(subject.get("type") or "").strip() or not str(subject.get("id") or "").strip():
        add_issue("missing_subject", "high", "review 缺少被审查对象类型或标识，无法绑定到证据链。")

    reviewer = review.get("reviewer") if isinstance(review.get("reviewer"), dict) else {}
    if not str(reviewer.get("kind") or "").strip() or not str(reviewer.get("id") or "").strip():
        add_issue("missing_reviewer", "high", "review 缺少 reviewer.kind 或 reviewer.id，无法审计审查来源。")

    if not str(review.get("comments") or "").strip():
        add_issue("missing_comments", "medium", "review 缺少说明，无法判断审查覆盖的证据、限制或风险。")

    if not review.get("evidence_refs"):
        add_issue("missing_evidence_refs", "high", "review 缺少 evidence_refs，不能支撑后续 decision record。")

    concerns = review.get("concerns") if isinstance(review.get("concerns"), list) else []
    if review.get("score") is None and not concerns:
        add_issue("missing_score_or_concerns", "medium", "review 缺少 score 或 concerns，难以比较审查质量和风险。")

    if review.get("verdict") == "completed" and concerns:
        high_concerns = [
            concern
            for concern in concerns
            if isinstance(concern, dict) and str(concern.get("severity") or "").lower() == "high"
        ]
        if high_concerns:
            add_issue("completed_with_high_concerns", "high", "review 标记 completed 但仍包含 high concerns，应降级或阻塞。")

    return issues


def build_review_audit(records: list[dict[str, Any]], *, q: str) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    issue_counts: dict[str, int] = {}
    review_ids_with_issues: list[str] = []
    high_issue_count = 0
    medium_issue_count = 0

    for review in records:
        issues = build_review_issues(review)
        for issue in issues:
            code = str(issue["code"])
            issue_counts[code] = issue_counts.get(code, 0) + 1
            if issue["severity"] == "high":
                high_issue_count += 1
            elif issue["severity"] == "medium":
                medium_issue_count += 1
        if issues:
            review_ids_with_issues.append(str(review.get("id")))

        item_state = "blocked" if any(issue["severity"] == "high" for issue in issues) else "degraded" if issues else "ready"
        subject = review.get("subject") if isinstance(review.get("subject"), dict) else {}
        reviewer = review.get("reviewer") if isinstance(review.get("reviewer"), dict) else {}
        items.append(
            {
                "review_id": review.get("id"),
                "subject": subject,
                "reviewer": reviewer,
                "verdict": review.get("verdict"),
                "status": review.get("status"),
                "state": item_state,
                "issues": issues,
            }
        )

    if high_issue_count:
        state = "blocked"
    elif medium_issue_count:
        state = "degraded"
    else:
        state = "ready"

    recommended_next_actions: list[dict[str, Any]] = []
    if issue_counts:
        recommended_next_actions.append(
            {
                "endpoint": "POST /api/v1/reviews",
                "reason": "重新写入包含 subject、reviewer、evidence_refs、comments、score 或 concerns 的审查事件。",
                "priority": "high" if high_issue_count else "normal",
            }
        )
    recommended_next_actions.append(
        {
            "endpoint": "POST /api/v1/decisions",
            "reason": "review audit 通过或缺口修复后，再写入 evidence-backed decision record。",
            "priority": "normal" if not high_issue_count else "low",
        }
    )

    return {
        "state": state,
        "query": q,
        "total": len(records),
        "issue_counts": issue_counts,
        "review_ids_with_issues": review_ids_with_issues,
        "items": items,
        "recommended_next_actions": recommended_next_actions,
        "safety": "ledger_only_no_critic_execution",
    }


def build_benchmark_audit(records: list[dict[str, Any]], *, q: str) -> dict[str, Any]:
    issue_counts: dict[str, int] = {}
    benchmark_ids_with_issues: list[str] = []
    items: list[dict[str, Any]] = []
    high_issue_count = 0

    def add_issue(issues: list[dict[str, Any]], code: str, message: str) -> None:
        nonlocal high_issue_count
        _increment_count(issue_counts, code)
        high_issue_count += 1
        issues.append({"code": code, "severity": "high", "message": message})

    for benchmark in records:
        issues: list[dict[str, Any]] = []
        external_runner = benchmark.get("external_runner") or {}
        metric_schema = benchmark.get("metric_schema") or {}
        input_schema = benchmark.get("input_schema") or {}
        output_schema = benchmark.get("output_schema") or {}
        artifact_requirements = benchmark.get("artifact_requirements") or []

        if not any(external_runner.get(key) for key in ["adapter", "name", "runner", "entrypoint"]):
            add_issue(
                issues,
                "missing_external_runner",
                "评测套件缺少外部适配器、运行方或入口，外部运行时无法稳定发现执行合同。",
            )
        if not metric_schema:
            add_issue(
                issues,
                "missing_metric_schema",
                "评测套件缺少指标合同，后续运行分数无法审计字段含义。",
            )
        if not input_schema:
            add_issue(
                issues,
                "missing_input_contract",
                "评测套件缺少输入合同，外部运行时无法判断需要哪些数据集、提示词或配置引用。",
            )
        if not output_schema:
            add_issue(
                issues,
                "missing_output_contract",
                "评测套件缺少输出合同，平台无法审计分数、成果引用和结果摘要是否齐全。",
            )
        if not artifact_requirements:
            add_issue(
                issues,
                "missing_artifact_requirements",
                "评测套件缺少成果要求，完成后无法确认应登记哪些结果、日志或数据引用。",
            )

        if issues:
            benchmark_ids_with_issues.append(benchmark["id"])

        items.append(
            {
                "id": benchmark["id"],
                "name": benchmark.get("name") or benchmark.get("title") or benchmark["id"],
                "domain": benchmark.get("domain", "general"),
                "status": benchmark.get("status"),
                "state": "blocked" if issues else "ready",
                "issues": issues,
                "contract_summary": {
                    "external_runner": external_runner.get("adapter")
                    or external_runner.get("name")
                    or external_runner.get("runner")
                    or external_runner.get("entrypoint")
                    or "",
                    "metric_keys": sorted(metric_schema.keys()),
                    "input_keys": sorted(input_schema.keys()),
                    "output_keys": sorted(output_schema.keys()),
                    "artifact_requirement_count": len(artifact_requirements),
                },
            }
        )

    state = "blocked" if high_issue_count else "ready"
    recommended_next_actions: list[dict[str, Any]] = []
    if issue_counts:
        recommended_next_actions.append(
            {
                "endpoint": "POST /api/v1/benchmarks",
                "reason": "重新登记或更新评测套件，补齐外部适配器、输入合同、输出合同、指标合同和成果要求。",
                "priority": "high",
            }
        )
    recommended_next_actions.append(
        {
            "endpoint": "POST /api/v1/benchmark-runs",
            "reason": "套件审计通过后，由外部运行时执行评测并登记运行状态、分数、成果引用和来源。",
            "priority": "normal" if not issue_counts else "low",
        }
    )

    return {
        "state": state,
        "query": q,
        "total": len(records),
        "issue_counts": issue_counts,
        "benchmark_ids_with_issues": benchmark_ids_with_issues,
        "items": items,
        "recommended_next_actions": recommended_next_actions,
        "safety": "registry_only_no_benchmark_execution",
    }


def build_benchmark_run_comparison(
    *,
    benchmark: dict[str, Any],
    runs: list[dict[str, Any]],
    metric: str | None,
) -> dict[str, Any]:
    metric_schema = benchmark.get("metric_schema") if isinstance(benchmark.get("metric_schema"), dict) else {}
    selected_metric = metric or next(iter(metric_schema.keys()), "")
    if not selected_metric:
        for run in runs:
            scores = run.get("scores") if isinstance(run.get("scores"), dict) else {}
            selected_metric = next(iter(scores.keys()), "")
            if selected_metric:
                break

    metric_contract = metric_schema.get(selected_metric) if selected_metric else {}
    if isinstance(metric_contract, dict):
        direction = str(metric_contract.get("direction") or "higher_is_better")
    else:
        direction = "lower_is_better" if str(metric_contract).lower() == "lower_is_better" else "higher_is_better"
    lower_is_better = direction == "lower_is_better"

    status_counts: dict[str, int] = {}
    issue_counts: dict[str, int] = {}
    run_ids_with_issues: list[str] = []
    ranked_runs: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []

    def add_issue(issues: list[dict[str, Any]], code: str, severity: str, message: str) -> None:
        _increment_count(issue_counts, code)
        issues.append({"code": code, "severity": severity, "message": message, "safety": "ledger_only_no_benchmark_execution"})

    for run in runs:
        status = str(run.get("status") or "planned")
        _increment_count(status_counts, status)
        scores = run.get("scores") if isinstance(run.get("scores"), dict) else {}
        raw_score = scores.get(selected_metric) if selected_metric else None
        score = raw_score if isinstance(raw_score, (int, float)) and not isinstance(raw_score, bool) else None
        artifact_refs = run.get("artifact_refs") if isinstance(run.get("artifact_refs"), list) else []
        provenance = run.get("provenance") if isinstance(run.get("provenance"), dict) else {}
        issues: list[dict[str, Any]] = []
        if selected_metric and score is None:
            add_issue(issues, "missing_metric_score", "high", f"run 缺少 numeric {selected_metric} 分数，无法参与可比排序。")
        if score is not None and not artifact_refs:
            add_issue(issues, "missing_artifact_refs", "medium", "run 有分数但缺少 artifact_refs，后续证据和复现审计较弱。")
        if score is not None and not provenance.get("runner"):
            add_issue(issues, "missing_runner_provenance", "medium", "run 有分数但缺少 provenance.runner，无法追踪外部执行方。")
        if status != "completed":
            add_issue(issues, "non_completed_status", "medium", "run 不是 completed，只能作为降级或失败上下文。")
        if issues:
            run_ids_with_issues.append(str(run.get("id")))

        item = {
            "run_id": run.get("id"),
            "benchmark_id": run.get("benchmark_id"),
            "status": status,
            "score": score,
            "artifact_ref_count": len(artifact_refs),
            "runner": provenance.get("runner") or "",
            "state": "blocked" if any(issue["severity"] == "high" for issue in issues) else "degraded" if issues else "ready",
            "issues": issues,
        }
        items.append(item)
        if score is not None:
            ranked_runs.append(item)

    ranked_runs.sort(key=lambda item: item["score"], reverse=not lower_is_better)
    scores = [float(item["score"]) for item in ranked_runs if item["score"] is not None]
    score_range = None
    if scores:
        score_range = {
            "min": min(scores),
            "max": max(scores),
            "delta": round(max(scores) - min(scores), 10),
        }

    if any(issue["severity"] == "high" for item in items for issue in item["issues"]):
        state = "blocked"
    elif issue_counts:
        state = "degraded"
    else:
        state = "ready"

    recommended_next_actions: list[dict[str, Any]] = []
    if issue_counts.get("missing_artifact_refs") or issue_counts.get("missing_runner_provenance"):
        recommended_next_actions.append(
            {
                "endpoint": "PATCH /api/v1/benchmark-runs/{run_id}",
                "reason": "补齐缺失的 artifact_refs 或 provenance.runner，使 run 可用于证据、审查和复现交接。",
                "priority": "normal",
            }
        )
    if ranked_runs:
        recommended_next_actions.append(
            {
                "endpoint": "POST /api/v1/evidence-records",
                "reason": "将最佳 run、baseline run 或冲突 run 写成 evidence record，再进入 review 和 decision。",
                "priority": "normal" if not issue_counts else "low",
            }
        )

    return {
        "schema": "autoresearch.benchmark_run_comparison.v1",
        "state": state,
        "benchmark_id": benchmark.get("id"),
        "metric": selected_metric,
        "direction": direction,
        "total": len(runs),
        "status_counts": status_counts,
        "best_run": ranked_runs[0] if ranked_runs else None,
        "score_range": score_range,
        "ranked_runs": ranked_runs,
        "items": items,
        "issue_counts": issue_counts,
        "run_ids_with_issues": run_ids_with_issues,
        "recommended_next_actions": recommended_next_actions,
        "safety": "read_only_benchmark_comparison_no_execution",
    }


def build_research_design_audit(
    *,
    questions: list[dict[str, Any]],
    hypotheses: list[dict[str, Any]],
    protocols: list[dict[str, Any]],
    q: str,
) -> dict[str, Any]:
    issue_counts: dict[str, int] = {}
    question_ids_with_issues: list[str] = []
    hypothesis_ids_with_issues: list[str] = []
    protocol_ids_with_issues: list[str] = []
    high_issue_count = 0
    medium_issue_count = 0

    def add_issue(
        issues: list[dict[str, Any]],
        code: str,
        severity: str,
        message: str,
    ) -> None:
        nonlocal high_issue_count, medium_issue_count
        _increment_count(issue_counts, code)
        if severity == "high":
            high_issue_count += 1
        elif severity == "medium":
            medium_issue_count += 1
        issues.append({"code": code, "severity": severity, "message": message})

    question_items: list[dict[str, Any]] = []
    for question in questions:
        issues: list[dict[str, Any]] = []
        if not question.get("success_criteria"):
            add_issue(
                issues,
                "question_missing_success_criteria",
                "high",
                "研究问题缺少成功标准，外部 Runtime 无法判断问题何时被回答。",
            )
        if not str(question.get("rationale") or "").strip():
            add_issue(
                issues,
                "question_missing_rationale",
                "medium",
                "研究问题缺少立项理由，后续 Agent 难以判断该问题为什么值得执行。",
            )
        if issues:
            question_ids_with_issues.append(question["id"])
        question_items.append(
            {
                "id": question["id"],
                "question": question.get("question", ""),
                "status": question.get("status"),
                "state": "blocked" if any(issue["severity"] == "high" for issue in issues) else "degraded" if issues else "ready",
                "issues": issues,
                "contract_summary": {
                    "has_success_criteria": bool(question.get("success_criteria")),
                    "has_rationale": bool(str(question.get("rationale") or "").strip()),
                    "program_id": question.get("program_id") or "",
                },
            }
        )

    hypothesis_items: list[dict[str, Any]] = []
    for hypothesis in hypotheses:
        issues: list[dict[str, Any]] = []
        if not str(hypothesis.get("expected_effect") or "").strip():
            add_issue(
                issues,
                "hypothesis_missing_expected_effect",
                "high",
                "假设缺少预期效应，无法判断预期变化方向和规模。",
            )
        if not hypothesis.get("acceptance_criteria"):
            add_issue(
                issues,
                "hypothesis_missing_acceptance_criteria",
                "high",
                "假设缺少接受标准，无法定义接受条件。",
            )
        if not hypothesis.get("rejection_criteria"):
            add_issue(
                issues,
                "hypothesis_missing_rejection_criteria",
                "high",
                "假设缺少拒绝标准，无法证伪或停止无效路径。",
            )
        if not (hypothesis.get("source_refs") or hypothesis.get("insight_refs")):
            add_issue(
                issues,
                "hypothesis_missing_source_trace",
                "medium",
                "假设缺少资料或洞察来源引用，证据来源链较弱。",
            )
        if issues:
            hypothesis_ids_with_issues.append(hypothesis["id"])
        hypothesis_items.append(
            {
                "id": hypothesis["id"],
                "title": hypothesis.get("title") or hypothesis.get("hypothesis") or hypothesis["id"],
                "status": hypothesis.get("status"),
                "state": "blocked" if any(issue["severity"] == "high" for issue in issues) else "degraded" if issues else "ready",
                "issues": issues,
                "contract_summary": {
                    "has_expected_effect": bool(str(hypothesis.get("expected_effect") or "").strip()),
                    "has_acceptance_criteria": bool(hypothesis.get("acceptance_criteria")),
                    "has_rejection_criteria": bool(hypothesis.get("rejection_criteria")),
                    "source_ref_count": len(hypothesis.get("source_refs") or []) + len(hypothesis.get("insight_refs") or []),
                },
            }
        )

    protocol_items: list[dict[str, Any]] = []
    for protocol in protocols:
        issues: list[dict[str, Any]] = []
        if not protocol.get("controls"):
            add_issue(
                issues,
                "protocol_missing_controls",
                "high",
                "预注册协议缺少 controls，无法比较唯一变化与基线。",
            )
        if not protocol.get("acceptance_criteria"):
            add_issue(
                issues,
                "protocol_missing_acceptance_criteria",
                "high",
                "预注册协议缺少接受标准，无法判断实验是否通过。",
            )
        if not protocol.get("rejection_criteria"):
            add_issue(
                issues,
                "protocol_missing_rejection_criteria",
                "high",
                "预注册协议缺少拒绝标准，无法判断实验何时失败或应停止。",
            )
        if not protocol.get("artifact_requirements"):
            add_issue(
                issues,
                "protocol_missing_artifact_requirements",
                "high",
                "预注册协议缺少成果要求，完成后无法确认需要登记哪些成果引用。",
            )
        if not protocol.get("method_id"):
            add_issue(
                issues,
                "protocol_missing_method_link",
                "medium",
                "预注册协议未关联方法卡，失败模式和所需成果类型的复用较弱。",
            )
        if not protocol.get("hypothesis_id"):
            add_issue(
                issues,
                "protocol_missing_hypothesis_link",
                "medium",
                "预注册协议未关联假设，后续 evidence 与 decision 绑定会更弱。",
            )
        if issues:
            protocol_ids_with_issues.append(protocol["id"])
        protocol_items.append(
            {
                "id": protocol["id"],
                "question_id": protocol.get("question_id"),
                "status": protocol.get("status"),
                "state": "blocked" if any(issue["severity"] == "high" for issue in issues) else "degraded" if issues else "ready",
                "issues": issues,
                "contract_summary": {
                    "has_method_id": bool(protocol.get("method_id")),
                    "has_hypothesis_id": bool(protocol.get("hypothesis_id")),
                    "controls": len(protocol.get("controls") or []),
                    "has_acceptance_criteria": bool(protocol.get("acceptance_criteria")),
                    "has_rejection_criteria": bool(protocol.get("rejection_criteria")),
                    "artifact_requirements": len(protocol.get("artifact_requirements") or []),
                    "one_change": protocol.get("one_change", ""),
                },
            }
        )

    if high_issue_count:
        state = "blocked"
    elif medium_issue_count:
        state = "degraded"
    else:
        state = "ready"

    recommended_next_actions: list[dict[str, Any]] = []
    if question_ids_with_issues:
        recommended_next_actions.append(
            {
                "endpoint": "POST /api/v1/research/questions",
                "reason": "补齐研究问题的立项理由和成功标准，让问题可回答、可审计。",
                "priority": "high" if high_issue_count else "normal",
            }
        )
    if hypothesis_ids_with_issues:
        recommended_next_actions.append(
            {
                "endpoint": "POST /api/v1/hypotheses",
                "reason": "补齐假设的预期效应、接受标准、拒绝标准和来源引用。",
                "priority": "high" if high_issue_count else "normal",
            }
        )
    if protocol_ids_with_issues:
        recommended_next_actions.append(
            {
                "endpoint": "POST /api/v1/research/protocols",
                "reason": "补齐协议的对照、接受/拒绝标准、成果要求、方法卡关联和假设关联。",
                "priority": "high" if high_issue_count else "normal",
            }
        )

    return {
        "state": state,
        "query": q,
        "issue_counts": issue_counts,
        "question_ids_with_issues": question_ids_with_issues,
        "hypothesis_ids_with_issues": hypothesis_ids_with_issues,
        "protocol_ids_with_issues": protocol_ids_with_issues,
        "questions": question_items,
        "hypotheses": hypothesis_items,
        "protocols": protocol_items,
        "recommended_next_actions": recommended_next_actions,
        "safety": "read_only_design_audit_no_execution",
    }


def validate_benchmark_completion(payload: dict[str, Any]) -> None:
    scores = payload.get("scores") or {}
    artifact_refs = payload.get("artifact_refs") or []
    provenance = payload.get("provenance") or {}
    if payload.get("status") == "completed" and scores and not artifact_refs and not provenance.get("runner"):
        raise HTTPException(
            status_code=422,
            detail="completed benchmark scores require artifact_refs or provenance.runner",
        )


def validate_decision_record(payload: dict[str, Any]) -> None:
    if not payload.get("evidence_refs"):
        raise HTTPException(status_code=422, detail="decision records require evidence_refs")


def validate_evidence_record(payload: dict[str, Any]) -> None:
    if not payload.get("evidence_refs"):
        raise HTTPException(status_code=422, detail="evidence records require evidence_refs")


def validate_research_round(payload: dict[str, Any]) -> None:
    if payload.get("status") == "completed" and not any(payload.get(field) for field in ROUND_TRACE_REF_FIELDS):
        raise HTTPException(
            status_code=422,
            detail="completed research rounds require implementation_refs, experiment_refs, artifact_refs, evidence_refs or decision_refs",
        )


def _round_ref_id(ref: dict[str, Any]) -> str | None:
    ref_id = ref.get("id") or ref.get("record_id")
    return str(ref_id) if ref_id else None


def build_research_round_detail(store: ResearchStore, round_record: dict[str, Any]) -> dict[str, Any]:
    unresolved_refs: list[dict[str, str]] = []
    trace: dict[str, Any] = {
        "worktree": round_record.get("worktree") or {},
        "implementation_refs": round_record.get("implementation_refs") or [],
        "experiments": [],
        "artifacts": [],
        "benchmark_runs": [],
        "evidence_records": [],
        "decisions": [],
        "unresolved_refs": unresolved_refs,
    }

    for field, (expected_type, collection, output_key) in ROUND_TRACE_REF_COLLECTIONS.items():
        for ref in round_record.get(field) or []:
            ref_id = _round_ref_id(ref)
            ref_type = str(ref.get("type") or expected_type)
            if not ref_id:
                unresolved_refs.append(
                    {
                        "field": field,
                        "type": ref_type,
                        "id": "",
                        "reason": "missing_id",
                    }
                )
                continue
            record = store.get_record(collection, ref_id)
            if not record:
                unresolved_refs.append(
                    {
                        "field": field,
                        "type": ref_type,
                        "id": ref_id,
                        "reason": "record_not_found",
                    }
                )
                continue
            trace[output_key].append(record)

    session = None
    if round_record.get("session_id"):
        session_id = str(round_record["session_id"])
        session = store.get_record("sessions", session_id)
        if not session:
            unresolved_refs.append(
                {
                    "field": "session_id",
                    "type": "session",
                    "id": session_id,
                    "reason": "record_not_found",
                }
            )

    recommended_next_actions: list[dict[str, Any]] = []
    if unresolved_refs:
        recommended_next_actions.append(
            {
                "action": "resolve_missing_round_refs",
                "endpoint": "PATCH /api/v1/research/rounds/{round_id}",
                "reason": "round has references that do not resolve to platform records",
            }
        )
    if not trace["experiments"]:
        recommended_next_actions.append(
            {
                "action": "register_or_link_experiment",
                "endpoint": "POST /api/v1/research/sessions/{session_id}/experiments",
                "reason": "round has no resolved experiment_refs",
            }
        )
    if not trace["artifacts"]:
        recommended_next_actions.append(
            {
                "action": "register_or_link_artifact",
                "endpoint": "POST /api/v1/research/sessions/{session_id}/artifacts",
                "reason": "round has no resolved artifact_refs",
            }
        )
    if not trace["evidence_records"]:
        recommended_next_actions.append(
            {
                "action": "create_evidence_record",
                "endpoint": "POST /api/v1/evidence-records",
                "reason": "round has no resolved evidence_refs",
            }
        )
    if not trace["decisions"]:
        recommended_next_actions.append(
            {
                "action": "create_decision_record",
                "endpoint": "POST /api/v1/decisions",
                "reason": "round has no resolved decision_refs",
            }
        )
    if round_record.get("status") != "completed" and any(
        round_record.get(field) for field in ROUND_TRACE_REF_FIELDS
    ):
        recommended_next_actions.append(
            {
                "action": "patch_round_status",
                "endpoint": "PATCH /api/v1/research/rounds/{round_id}",
                "reason": "round has trace references but is not completed",
            }
        )

    return {
        "round": round_record,
        "session": session,
        "trace": trace,
        "recommended_next_actions": recommended_next_actions,
        "safety": "read_only_round_trace_no_execution_no_graph",
    }


def build_research_readiness(
    store: ResearchStore,
    *,
    query: str,
    claim: str,
    round_id: str,
    stage: str,
    limit: int,
) -> dict[str, Any]:
    context = build_research_context(store, query=query, claim=claim, limit=limit)
    round_trace = None
    warnings: list[str] = []
    checks: list[dict[str, Any]] = []
    recommended_next_actions: list[dict[str, Any]] = []

    def add_check(
        check_id: str,
        status: str,
        title: str,
        detail: str,
        *,
        severity: str = "required",
        action: dict[str, Any] | None = None,
    ) -> None:
        check = {
            "id": check_id,
            "status": status,
            "title": title,
            "detail": detail,
            "severity": severity,
        }
        if action:
            check["recommended_action"] = action
            recommended_next_actions.append(action)
        checks.append(check)

    if round_id:
        round_record = require_record(store.get_record("research_rounds", round_id), round_id)
        round_trace = build_research_round_detail(store, round_record)
        unresolved_count = len(round_trace["trace"]["unresolved_refs"])
        if unresolved_count:
            warnings.append(f"unresolved round refs: {unresolved_count}")
            add_check(
                "round_trace_refs",
                "fail",
                "轮次追踪引用",
                "研究轮次包含未解析引用，不能作为完整证据。",
                action={
                    "action": "resolve_missing_round_refs",
                    "endpoint": "PATCH /api/v1/research/rounds/{round_id}",
                    "reason": "round has unresolved_refs",
                },
            )
        else:
            add_check("round_trace_refs", "pass", "轮次追踪引用", "研究轮次引用均可解析。")
    else:
        add_check(
            "round_trace_refs",
            "warn",
            "轮次追踪引用",
            "没有提供 round_id，无法校验本轮 worktree、commit、实验、artifact、证据和决策引用。",
            severity="recommended",
            action={
                "action": "create_or_select_research_round",
                "endpoint": "POST /api/v1/research/rounds",
                "reason": "readiness check should be tied to a round when possible",
            },
        )

    if context["risk_flags"]:
        add_check(
            "context_risks",
            "warn",
            "上下文风险",
            "上下文中存在 blocked、degraded 或 failed 记录。",
            severity="recommended",
            action={
                "action": "inspect_context_risk_flags",
                "endpoint": "GET /api/v1/research/context",
                "reason": "risk_flags should be reviewed before continuing",
            },
        )
    else:
        add_check("context_risks", "pass", "上下文风险", "没有发现阻塞、降级或失败风险。")

    if round_trace and round_trace["trace"]["experiments"]:
        add_check("experiment_preregistration", "pass", "实验预注册", "轮次已关联预注册实验。")
    elif context["counts"].get("experiments", 0):
        add_check(
            "experiment_preregistration",
            "warn",
            "实验预注册",
            "上下文中存在实验，但当前轮次没有解析到 experiment_refs。",
            severity="recommended",
            action={
                "action": "link_experiment_to_round",
                "endpoint": "PATCH /api/v1/research/rounds/{round_id}",
                "reason": "round should point to the experiment it relies on",
            },
        )
    else:
        add_check(
            "experiment_preregistration",
            "warn",
            "实验预注册",
            "没有找到预注册实验。",
            severity="recommended",
            action={
                "action": "register_experiment",
                "endpoint": "POST /api/v1/research/sessions/{session_id}/experiments",
                "reason": "formal research should preregister hypothesis and criteria",
            },
        )

    evidence_state = context["evidence_summary"]["state"]
    if evidence_state in {"supported", "contested", "needs_replication"}:
        status = "warn" if evidence_state in {"contested", "needs_replication"} else "pass"
        severity = "required" if evidence_state == "contested" else "recommended"
        add_check(
            "evidence_summary",
            status,
            "证据概览",
            f"证据状态为 {evidence_state}。",
            severity=severity,
            action=(
                {
                    "action": "investigate_evidence_state",
                    "endpoint": "GET /api/v1/evidence-records/summary",
                    "reason": f"evidence state is {evidence_state}",
                }
                if status == "warn"
                else None
            ),
        )
    else:
        add_check(
            "evidence_summary",
            "fail" if stage in {"before_review", "before_decision", "before_curation"} else "warn",
            "证据概览",
            f"证据状态为 {evidence_state}，还不能支撑审查、决策或经验维护。",
            action={
                "action": "create_evidence_record",
                "endpoint": "POST /api/v1/evidence-records",
                "reason": "claim needs evidence before review or decision",
            },
        )

    if stage in {"before_decision", "before_curation"}:
        if round_trace and round_trace["trace"]["decisions"]:
            add_check("decision_record", "pass", "决策记录", "轮次已关联决策记录。")
        else:
            add_check(
                "decision_record",
                "warn",
                "决策记录",
                "尚未找到与本轮关联的决策记录。",
                severity="recommended",
                action={
                    "action": "create_decision_record",
                    "endpoint": "POST /api/v1/decisions",
                    "reason": "evidence-backed decisions should be recorded explicitly",
                },
            )

    blocking_gaps = [check for check in checks if check["status"] == "fail"]
    warning_gaps = [check for check in checks if check["status"] == "warn"]
    if blocking_gaps:
        state = "blocked"
    elif warning_gaps:
        state = "degraded"
    else:
        state = "ready"

    deduped_actions: list[dict[str, Any]] = []
    seen_actions: set[tuple[str, str]] = set()
    for action in recommended_next_actions + context["recommended_next_actions"]:
        key = (str(action.get("action") or ""), str(action.get("endpoint") or ""))
        if key not in seen_actions:
            seen_actions.add(key)
            deduped_actions.append(action)

    return {
        "query": query,
        "claim": claim,
        "stage": stage,
        "state": state,
        "checks": checks,
        "blocking_gaps": blocking_gaps,
        "warning_gaps": warning_gaps,
        "warnings": warnings,
        "context": context,
        "round_trace": round_trace,
        "recommended_next_actions": deduped_actions,
        "safety": "read_only_readiness_check_no_execution",
    }


def _increment_count(counter: dict[str, int], key: str) -> None:
    counter[key] = counter.get(key, 0) + 1


def _sorted_values(values: set[str]) -> list[str]:
    return sorted(value for value in values if value)


def build_evidence_coverage(records: list[dict[str, Any]]) -> dict[str, Any]:
    evidence_kinds: dict[str, int] = {}
    evidence_ref_types: dict[str, int] = {}
    sessions: set[str] = set()
    subjects: set[str] = set()

    for record in records:
        _increment_count(evidence_kinds, str(record.get("evidence_kind") or "unknown"))

        session_id = record.get("session_id")
        if session_id:
            sessions.add(str(session_id))

        subject = record.get("subject") if isinstance(record.get("subject"), dict) else {}
        subject_type = str(subject.get("type") or "").strip()
        subject_id = str(subject.get("id") or "").strip()
        if subject_type and subject_id:
            subjects.add(f"{subject_type}:{subject_id}")

        for ref in record.get("evidence_refs") or []:
            if isinstance(ref, dict):
                _increment_count(evidence_ref_types, str(ref.get("type") or "unknown"))

    return {
        "evidence_kinds": evidence_kinds,
        "evidence_ref_types": evidence_ref_types,
        "sessions": _sorted_values(sessions),
        "subjects": _sorted_values(subjects),
    }


def build_evidence_quality_gaps(
    *,
    records: list[dict[str, Any]],
    stances: dict[str, int],
    limitations: list[str],
    coverage: dict[str, Any],
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    positive = stances.get("supports", 0) + stances.get("replicates", 0)
    negative = stances.get("contradicts", 0) + stances.get("fails_to_replicate", 0)
    has_replication = stances.get("replicates", 0) + stances.get("fails_to_replicate", 0) > 0

    if positive and not has_replication:
        gaps.append(
            {
                "code": "missing_replication",
                "severity": "high",
                "message": "已有支持证据但缺少独立复现或复现失败记录。",
            }
        )
    if positive and negative:
        gaps.append(
            {
                "code": "conflicting_evidence",
                "severity": "high",
                "message": "同一主张同时存在支持与反证，需要先做审查。",
            }
        )
    if records and len(coverage.get("sessions") or []) <= 1:
        gaps.append(
            {
                "code": "single_session_evidence",
                "severity": "medium",
                "message": "证据只覆盖一个或未标注 session，跨轮次稳健性不足。",
            }
        )
    if records and not coverage.get("subjects"):
        gaps.append(
            {
                "code": "missing_subject_binding",
                "severity": "medium",
                "message": "证据没有绑定 hypothesis、experiment、benchmark 或 artifact 对象。",
            }
        )
    if records and not limitations:
        gaps.append(
            {
                "code": "missing_limitations",
                "severity": "low",
                "message": "证据没有记录限制，审查时难以判断外部效度和失败条件。",
            }
        )

    medium_or_low_ids: list[str] = []
    for record in records:
        quality = record.get("quality") if isinstance(record.get("quality"), dict) else {}
        confidence = str(quality.get("confidence") or "unknown").lower()
        if confidence in {"medium", "low", "unknown"}:
            medium_or_low_ids.append(str(record.get("id")))
    if medium_or_low_ids:
        gaps.append(
            {
                "code": "medium_or_low_confidence",
                "severity": "medium",
                "message": "部分证据置信度不是 high，决策前需要补充质量说明或复现。",
                "evidence_ids": medium_or_low_ids,
            }
        )

    return gaps[:20]


def build_evidence_replication_plan(
    *,
    quality_gaps: list[dict[str, Any]],
    state: str,
) -> list[dict[str, Any]]:
    gap_codes = {str(gap.get("code")) for gap in quality_gaps}
    plan: list[dict[str, Any]] = []

    if "missing_replication" in gap_codes:
        plan.append(
            {
                "action": "register_independent_replication",
                "endpoint": "POST /api/v1/research/protocols",
                "reason": "为同一主张登记独立复现实验协议，明确 one_change、controls、接受和拒绝标准。",
                "priority": "high",
            }
        )
        plan.append(
            {
                "action": "write_replication_evidence",
                "endpoint": "POST /api/v1/evidence-records",
                "reason": "复现实验结束后写入 replicates 或 fails_to_replicate 证据记录。",
                "priority": "high",
            }
        )
    if "single_session_evidence" in gap_codes:
        plan.append(
            {
                "action": "collect_cross_session_evidence",
                "endpoint": "POST /api/v1/evidence-records",
                "reason": "从不同 session、runner 或数据切片登记第二条可追溯证据。",
                "priority": "normal",
            }
        )
    if state == "contested":
        plan.append(
            {
                "action": "open_conflict_review",
                "endpoint": "POST /api/v1/reviews",
                "reason": "支持与反证冲突时先审查证据质量和实验差异，再写入决策。",
                "priority": "high",
            }
        )

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in plan:
        key = (str(item["action"]), str(item["endpoint"]))
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped[:10]


def summarize_evidence_claim(records: list[dict[str, Any]], claim: str) -> dict[str, Any]:
    normalized_claim = claim.strip().lower()
    matching = [
        record
        for record in records
        if str(record.get("claim", "")).strip().lower() == normalized_claim
    ]
    stances = {stance: 0 for stance in EVIDENCE_STANCES}
    confidence: dict[str, int] = {}
    limitations: list[str] = []
    evidence_ids: list[str] = []

    for record in matching:
        stance = str(record.get("stance") or "inconclusive")
        stances.setdefault(stance, 0)
        stances[stance] += 1
        evidence_ids.append(str(record.get("id")))

        quality = record.get("quality") if isinstance(record.get("quality"), dict) else {}
        confidence_key = str(quality.get("confidence") or "unknown")
        confidence[confidence_key] = confidence.get(confidence_key, 0) + 1

        for limitation in record.get("limitations") or []:
            if isinstance(limitation, str) and limitation and limitation not in limitations:
                limitations.append(limitation)

    positive = stances.get("supports", 0) + stances.get("replicates", 0)
    negative = stances.get("contradicts", 0) + stances.get("fails_to_replicate", 0)
    uncertain = stances.get("mixed", 0) + stances.get("inconclusive", 0)
    has_replication = stances.get("replicates", 0) + stances.get("fails_to_replicate", 0) > 0

    if not matching:
        state = "insufficient"
        recommended_next_action = "create_evidence_record"
    elif positive and negative:
        state = "contested"
        recommended_next_action = "investigate_conflict"
    elif negative:
        state = "contradicted"
        recommended_next_action = "open_review"
    elif positive and not has_replication:
        state = "needs_replication"
        recommended_next_action = "register_replication"
    elif positive:
        state = "supported"
        recommended_next_action = "open_review"
    elif uncertain:
        state = "insufficient"
        recommended_next_action = "collect_more_evidence"
    else:
        state = "insufficient"
        recommended_next_action = "collect_more_evidence"

    coverage = build_evidence_coverage(matching)
    quality_gaps = build_evidence_quality_gaps(
        records=matching,
        stances=stances,
        limitations=limitations,
        coverage=coverage,
    )
    replication_plan = build_evidence_replication_plan(quality_gaps=quality_gaps, state=state)

    return {
        "claim": claim,
        "total": len(matching),
        "state": state,
        "recommended_next_action": recommended_next_action,
        "stances": stances,
        "confidence": confidence,
        "evidence_ids": evidence_ids,
        "limitations": limitations[:20],
        "coverage": coverage,
        "quality_gaps": quality_gaps,
        "replication_plan": replication_plan,
        "matching_strategy": "exact_claim_case_insensitive",
    }


def build_research_risk_flags(sections: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    for collection, items in sections.items():
        for item in items:
            status = str(item.get("status") or "")
            event_type = str(item.get("event_type") or "")
            if status in RISK_STATUSES or event_type == "blocker":
                flags.append(
                    {
                        "collection": collection,
                        "id": item.get("id"),
                        "kind": event_type or collection,
                        "status": status or "blocked",
                        "title": item.get("title") or item.get("hypothesis") or item.get("name") or item.get("id"),
                    }
                )
    return flags[:20]


def _append_action(
    actions: list[dict[str, Any]],
    *,
    endpoint: str,
    reason: str,
    priority: str = "normal",
) -> None:
    if any(action["endpoint"] == endpoint and action["reason"] == reason for action in actions):
        return
    actions.append({"endpoint": endpoint, "reason": reason, "priority": priority})


def build_research_context_actions(
    *,
    sections: dict[str, list[dict[str, Any]]],
    evidence_summary: dict[str, Any],
    risk_flags: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if not sections["sources"]:
        _append_action(
            actions,
            endpoint="POST /api/v1/sources",
            reason="缺少可追溯资料输入，先登记论文、数据集、仓库或 artifact 引用。",
            priority="high",
        )
    if sections["sources"] and not sections["insights"]:
        _append_action(
            actions,
            endpoint="POST /api/v1/insights",
            reason="已有资料但缺少洞察，需要把资料转成可验证线索。",
            priority="high",
        )
    if sections["insights"] and not sections["hypotheses"]:
        _append_action(
            actions,
            endpoint="POST /api/v1/hypotheses",
            reason="已有洞察但缺少可检验假设。",
            priority="high",
        )
    if sections["hypotheses"] and not sections["protocols"]:
        _append_action(
            actions,
            endpoint="POST /api/v1/research/protocols",
            reason="已有假设但缺少预注册协议、对照和接受/拒绝标准。",
            priority="high",
        )
    if sections["hypotheses"] and not sections["sessions"]:
        _append_action(
            actions,
            endpoint="POST /api/v1/research/sessions",
            reason="已有研究对象但缺少 session ledger 承接后续过程。",
            priority="normal",
        )

    evidence_action = evidence_summary.get("recommended_next_action")
    if evidence_action == "create_evidence_record":
        _append_action(
            actions,
            endpoint="POST /api/v1/evidence-records",
            reason="当前主张缺少证据记录，不能进入审查或决策。",
            priority="high",
        )
    elif evidence_action == "register_replication":
        _append_action(
            actions,
            endpoint="POST /api/v1/research/protocols",
            reason="证据已有支持但缺少复现，应登记复现实验协议。",
            priority="high",
        )
    elif evidence_action == "investigate_conflict":
        _append_action(
            actions,
            endpoint="POST /api/v1/reviews",
            reason="证据存在支持与反证冲突，需要自动 critic 或外部 Runtime 审查。",
            priority="high",
        )
    elif evidence_action == "open_review":
        _append_action(
            actions,
            endpoint="POST /api/v1/reviews",
            reason="证据已足够进入审查事件，但不能跳过 evidence-backed review。",
            priority="normal",
        )
    elif evidence_action == "collect_more_evidence":
        _append_action(
            actions,
            endpoint="POST /api/v1/sources",
            reason="当前证据仍不确定，需要继续登记资料或 artifact 引用。",
            priority="normal",
        )

    if sections["reviews"] and not sections["decisions"]:
        _append_action(
            actions,
            endpoint="POST /api/v1/decisions",
            reason="已有审查但缺少证据绑定科研决策。",
            priority="normal",
        )
    if risk_flags:
        _append_action(
            actions,
            endpoint="GET /api/v1/research/events",
            reason="存在阻塞、失败或降级记录，恢复研究前应先读取过程审计。",
            priority="high",
        )
    return actions[:10]


def build_research_context(
    store: ResearchStore,
    *,
    query: str,
    claim: str,
    limit: int,
) -> dict[str, Any]:
    sections = {
        name: store.query_records(collection, status=None, q=query, limit=limit, offset=0, sort="-created_at")[
            "items"
        ]
        for name, collection in RESEARCH_CONTEXT_COLLECTIONS.items()
    }
    claim_for_summary = claim.strip() or query.strip()
    evidence_records = store.query_records(
        "evidence_records",
        status="completed",
        q=claim_for_summary,
        limit=500,
        offset=0,
        sort="-created_at",
    )["items"]
    evidence_summary = summarize_evidence_claim(evidence_records, claim_for_summary)
    risk_flags = build_research_risk_flags(sections)
    actions = build_research_context_actions(
        sections=sections,
        evidence_summary=evidence_summary,
        risk_flags=risk_flags,
    )
    if risk_flags:
        state = "needs_recovery"
    elif evidence_summary["state"] in {"contested", "needs_replication", "insufficient"}:
        state = evidence_summary["state"]
    elif actions:
        state = "needs_next_step"
    else:
        state = "ready_for_review"

    return {
        "query": query,
        "claim": claim_for_summary,
        "state": state,
        "counts": {name: len(items) for name, items in sections.items()},
        "sections": sections,
        "evidence_summary": evidence_summary,
        "risk_flags": risk_flags,
        "recommended_next_actions": actions,
        "matching_strategy": "json_text_contains_query_with_exact_claim_evidence_summary",
        "safety": "read_only_context_pack_no_execution",
    }


def _dedupe_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for action in actions:
        key = (
            str(action.get("action") or ""),
            str(action.get("endpoint") or ""),
            str(action.get("reason") or ""),
        )
        if key not in seen:
            seen.add(key)
            deduped.append(action)
    return deduped


def build_reproducibility_package(
    *,
    context: dict[str, Any],
    session_ledger: dict[str, Any] | None,
    round_trace: dict[str, Any] | None,
    artifacts: list[dict[str, Any]],
    artifact_audit: dict[str, Any],
    review_audit: dict[str, Any],
) -> dict[str, Any]:
    checklist: list[dict[str, Any]] = []

    def add_check(
        check_id: str,
        label: str,
        status: str,
        evidence: list[str],
        detail: str,
        severity: str = "required",
    ) -> None:
        checklist.append(
            {
                "id": check_id,
                "label": label,
                "status": status,
                "severity": severity,
                "evidence": evidence,
                "detail": detail,
            }
        )

    session_id = ""
    if session_ledger and isinstance(session_ledger.get("session"), dict):
        session_id = str(session_ledger["session"].get("id") or "")
    add_check(
        "session_ledger",
        "研究账本",
        "pass" if session_id else "warn",
        [session_id] if session_id else [],
        "已包含 session ledger，可恢复过程事件、实验和成果引用。"
        if session_id
        else "未指定 session，导出包只能依赖关键词上下文。",
        severity="recommended",
    )

    unresolved_refs = []
    round_id = ""
    if round_trace:
        round_id = str(round_trace.get("round", {}).get("id") or "")
        unresolved_refs = round_trace.get("trace", {}).get("unresolved_refs") or []
    add_check(
        "round_trace",
        "研究轮次追踪",
        "pass" if round_trace and not unresolved_refs else "fail" if unresolved_refs else "warn",
        [round_id] if round_id else [],
        "轮次引用均已解析。"
        if round_trace and not unresolved_refs
        else f"存在未解析引用 {len(unresolved_refs)} 个。"
        if unresolved_refs
        else "未指定研究轮次，无法校验每轮方案引用链。",
    )

    artifact_ids = [str(artifact.get("id")) for artifact in artifacts if artifact.get("id")]
    add_check(
        "artifact_metadata",
        "成果引用元数据",
        "pass" if artifact_audit.get("state") == "ready" else "fail" if artifact_audit.get("state") == "blocked" else "warn",
        artifact_ids,
        f"artifact audit state={artifact_audit.get('state')}，数量={artifact_audit.get('total')}。",
    )

    add_check(
        "review_gate",
        "审查质量门",
        "pass" if review_audit.get("state") == "ready" else "fail" if review_audit.get("state") == "blocked" else "warn",
        [str(item.get("id")) for item in review_audit.get("items") or [] if item.get("id")],
        f"review audit state={review_audit.get('state')}，数量={review_audit.get('total')}。",
    )

    evidence_summary = context.get("evidence_summary") or {}
    evidence_state = str(evidence_summary.get("state") or "unknown")
    add_check(
        "evidence_summary",
        "证据概览",
        "pass" if evidence_state == "supported" else "warn" if evidence_state in {"needs_replication", "contested"} else "fail",
        [str(record_id) for record_id in evidence_summary.get("evidence_ids") or []],
        f"evidence state={evidence_state}，quality_gaps={len(evidence_summary.get('quality_gaps') or [])}。",
    )

    external_artifacts = [
        {
            "id": artifact.get("id"),
            "title": artifact.get("title"),
            "artifact_type": artifact.get("artifact_type"),
            "uri": artifact.get("uri"),
            "sha256": artifact.get("sha256"),
            "mime_type": artifact.get("mime_type"),
            "size_bytes": artifact.get("size_bytes"),
            "storage": artifact.get("storage"),
            "summary": artifact.get("summary"),
            "requires_external_verification": bool(artifact.get("uri")),
            "platform_read": False,
        }
        for artifact in artifacts
    ]

    if any(check["status"] == "fail" for check in checklist):
        state = "blocked"
    elif any(check["status"] == "warn" for check in checklist):
        state = "degraded"
    else:
        state = "ready"

    return {
        "schema": "autoresearch.reproducibility.v1",
        "state": state,
        "checklist": checklist,
        "external_artifacts": external_artifacts,
        "handoff_steps": [
            "外部 Runtime 使用 session_ledger 恢复过程事件、实验和收尾复盘。",
            "外部 Runtime 使用 round_trace 校验 worktree、commit、实验、artifact、证据和决策引用。",
            "外部 Runtime 在自己的环境中验证 external_artifacts 的 URI、hash、大小和可访问性。",
            "外部 Runtime 根据 evidence_summary、artifact_audit 和 review_audit 的缺口决定复现、补证或进入决策。",
        ],
        "safety": "read_only_reproducibility_manifest_no_external_artifact_access",
    }


def build_research_audit_export(
    store: ResearchStore,
    *,
    query: str,
    claim: str,
    session_id: str,
    round_id: str,
    limit: int,
) -> dict[str, Any]:
    context = build_research_context(store, query=query, claim=claim, limit=limit)

    session_ledger = None
    if session_id:
        session_ledger = store.session_detail(session_id)

    round_trace = None
    if round_id:
        round_record = require_record(store.get_record("research_rounds", round_id), round_id)
        round_trace = build_research_round_detail(store, round_record)

    artifacts = store.query_records(
        "artifacts",
        status=None,
        q=query,
        limit=500,
        offset=0,
        sort="-created_at",
    )["items"]
    if session_id:
        artifacts = [artifact for artifact in artifacts if str(artifact.get("session_id") or "") == session_id]
    artifact_audit = build_artifact_audit(artifacts, q=query, session_id=session_id or None)

    reviews = store.query_records(
        "reviews",
        status=None,
        q=query,
        limit=500,
        offset=0,
        sort="-created_at",
    )["items"]
    review_audit = build_review_audit(reviews, q=query)

    warnings: list[str] = []
    if round_trace and round_trace["trace"]["unresolved_refs"]:
        warnings.append(f"unresolved round refs: {len(round_trace['trace']['unresolved_refs'])}")
    if artifact_audit["state"] != "ready":
        warnings.append(f"artifact audit state: {artifact_audit['state']}")
    if review_audit["state"] != "ready":
        warnings.append(f"review audit state: {review_audit['state']}")

    artifact_ids = sorted(
        {
            str(artifact.get("id"))
            for artifact in artifacts
            if artifact.get("id")
        }
    )

    recommended_next_actions = _dedupe_actions(
        context["recommended_next_actions"]
        + (round_trace["recommended_next_actions"] if round_trace else [])
        + artifact_audit["recommended_next_actions"]
        + review_audit["recommended_next_actions"]
    )
    reproducibility = build_reproducibility_package(
        context=context,
        session_ledger=session_ledger,
        round_trace=round_trace,
        artifacts=artifacts,
        artifact_audit=artifact_audit,
        review_audit=review_audit,
    )

    return {
        "bundle_id": f"audit_export_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
        "generated_at": datetime.now(UTC).isoformat(),
        "filters": {
            "query": query,
            "claim": context["claim"],
            "session_id": session_id,
            "round_id": round_id,
            "limit": limit,
        },
        "manifest": {
            "schema": "autoresearch.audit_bundle.v1",
            "record_counts": context["counts"],
            "included_sections": [
                section for section, count in context["counts"].items() if count > 0
            ],
            "warnings": warnings,
        },
        "context": context,
        "session_ledger": session_ledger,
        "round_trace": round_trace,
        "artifact_audit": artifact_audit,
        "review_audit": review_audit,
        "reproducibility": reproducibility,
        "integrity": {
            "external_reads": False,
            "external_writes": False,
            "included_artifact_refs": artifact_ids,
            "artifact_payload_policy": "references_only_no_blob_export",
        },
        "recommended_next_actions": recommended_next_actions,
        "safety": "read_only_audit_export_no_execution_no_external_read",
    }


@router.get(
    "/capabilities",
    tags=["capabilities"],
    response_model=ApiEnvelope,
    summary="读取外部 Runtime 能力目录",
    openapi_extra=agent_guidance(
        when_to_use="外部 Runtime 启动前发现平台能力、入口 endpoint 和安全边界。",
        facts_from="OpenAPI x-agent-capabilities",
        capability_group="capabilities",
        safety_level="read",
    ),
)
def list_capabilities() -> ApiEnvelope:
    return envelope(AGENT_CAPABILITIES)


@router.get(
    "/agent/onboarding",
    tags=["system"],
    response_model=ApiEnvelope,
    summary="读取外部 Agent 接入自检包",
    openapi_extra=agent_guidance(
        when_to_use="外部 Agent 或 Runtime 首次接入平台时，聚合读取认证、部署就绪、能力目录、Skill 加载顺序和建议首批调用。",
        facts_from="system security, system readiness, OpenAPI x-agent-capabilities, auto-research skill references",
        next_steps=[
            "GET /api/v1/openapi.json",
            "GET /api/v1/system/security",
            "GET /api/v1/system/readiness",
            "POST /api/v1/experiences/query",
            "GET /api/v1/research/context",
        ],
        capability_group="platform_readiness",
        safety_level="read",
        safety="只读接入自检包，不读取外部 Runtime、不访问 artifact URI、不执行实验、不返回 OpenAPI 全量正文。",
        response_contract="返回 schema、state、openapi、docs、skill、security、readiness、capability_count、capability_groups、recommended_first_calls、recommended_next_actions、integrity 和 safety。",
    ),
)
def agent_onboarding(store: ResearchStore = Depends(get_store)) -> ApiEnvelope:
    settings = get_settings()
    return envelope(
        build_agent_onboarding(
            store,
            api_prefix=settings.api_prefix,
            api_token=settings.api_token,
        )
    )


@router.get(
    "/system/status",
    tags=["system"],
    response_model=ApiEnvelope,
    summary="读取平台状态",
    openapi_extra=agent_guidance(
        when_to_use="检查 API 和本地 store 是否可用，不触发任何研究执行。",
        facts_from="local platform store",
        capability_group="system",
        safety_level="read",
    ),
)
def system_status(store: ResearchStore = Depends(get_store)) -> ApiEnvelope:
    return envelope({"status": "ok", **store.health()})


@router.get(
    "/system/readiness",
    tags=["system"],
    response_model=ApiEnvelope,
    summary="读取系统部署就绪检查",
    openapi_extra=agent_guidance(
        when_to_use="部署、发布或外部 Runtime 接入前，检查 store、PostgreSQL schema 合同和旧模块排除状态。",
        facts_from="store health, alembic migration contract",
        next_steps=["GET /api/v1/system/status", "GET /api/v1/openapi.json"],
        capability_group="system",
        safety_level="read",
        safety="只读本平台配置和迁移合同，不访问外部 Runtime、不连接外部 artifact URI、不执行迁移。",
        response_contract="返回 state、checks、store、schema_contract、recommended_next_actions 和 safety。",
    ),
)
def system_readiness(store: ResearchStore = Depends(get_store)) -> ApiEnvelope:
    return envelope(build_system_readiness(store))


@router.get(
    "/system/security",
    tags=["system"],
    response_model=ApiEnvelope,
    summary="读取系统安全配置状态",
    openapi_extra=agent_guidance(
        when_to_use="外部 Runtime 或部署人员在正式接入前确认 API token、公开 endpoint 和审计边界。",
        facts_from="runtime security settings",
        next_steps=["GET /api/v1/system/readiness", "GET /api/v1/system/audit-log"],
        capability_group="system",
        safety_level="read",
        safety="只返回是否启用认证、公开 endpoint 和审计策略，不回显 token。",
        response_contract="返回 auth_required、auth_scheme、protected_scope、public_endpoints、audit 和 safety。",
    ),
)
def system_security() -> ApiEnvelope:
    settings = get_settings()
    return envelope(security_status(settings.api_prefix, settings.api_token))


@router.get(
    "/system/audit-log",
    tags=["system"],
    response_model=ApiEnvelope,
    summary="读取 API 请求审计日志",
    openapi_extra=agent_guidance(
        when_to_use="部署人员或外部 Runtime 需要审计写操作、拒绝请求、actor 和状态码时读取。",
        facts_from="logs collection",
        capability_group="system",
        safety_level="read",
        safety="只读平台内请求元数据，不包含请求正文、不访问外部 Runtime 或 artifact URI。",
        response_contract="返回标准 list envelope data: items,total,limit,offset,sort。",
    ),
)
def system_audit_log(
    q: str = "",
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort: str = "-created_at",
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    return query_records(store, "logs", status=None, q=q, limit=limit, offset=offset, sort=sort)


@router.get(
    "/method-loop",
    tags=["method-loop"],
    response_model=ApiEnvelope,
    summary="读取 AutoResearch 方法论闭环",
    openapi_extra=agent_guidance(
        when_to_use="外部 Runtime 首次接入或恢复研究前，读取 FARS/Karpathy 风格的 canonical 主路径和当前 API 映射。",
        facts_from="method loop contract, store health",
        next_steps=[
            "POST /api/v1/ideas",
            "POST /api/v1/hypotheses",
            "POST /api/v1/plans",
            "POST /api/v1/results",
            "POST /api/v1/experiences/curation/preview",
        ],
        capability_group="method_loop",
        safety_level="read",
        safety="只读方法论和本平台 collection 计数，不执行实验、不读取外部 artifact。",
        response_contract="返回 schema、loop、stages、counts、recommended_flow 和 safety。",
    ),
)
def method_loop(store: ResearchStore = Depends(get_store)) -> ApiEnvelope:
    collections = store.health().get("collections", {})
    stages = []
    for stage in METHOD_LOOP_STAGES:
        stages.append(
            {
                **stage,
                "count": collections.get(stage["backing_collection"], 0),
            }
        )
    return envelope(
        {
            "schema": "autoresearch.method_loop.v1",
            "loop": "Idea Pool -> Hypothesis -> Plan -> Experiment -> Result -> Review -> Decision -> Lesson -> Next Hypothesis",
            "stages": stages,
            "recommended_flow": [
                "GET /api/v1/method-loop",
                "POST /api/v1/ideas",
                "POST /api/v1/hypotheses",
                "POST /api/v1/plans",
                "POST /api/v1/research/sessions",
                "POST /api/v1/results",
                "POST /api/v1/reviews",
                "POST /api/v1/decisions",
                "POST /api/v1/experiences/curation/preview",
                "POST /api/v1/experiences/curation/apply",
            ],
            "safety": {
                "executes_runtime": False,
                "reads_external_artifacts": False,
                "stores_large_payloads": False,
            },
        }
    )


@router.post(
    "/ideas",
    tags=["method-loop"],
    response_model=ApiEnvelope,
    summary="创建 idea pool 输入",
    openapi_extra=agent_guidance(
        when_to_use="写入论文、repo、benchmark gap、研究员想法、历史失败或外部观察，作为 hypothesis 来源。",
        facts_from="external Runtime, researcher idea pool, papers, repos, benchmark gaps",
        next_steps=["POST /api/v1/hypotheses", "GET /api/v1/method-loop"],
        capability_group="method_loop",
        response_contract="写入 sources backing collection，并标记 metadata.loop_stage=idea_pool。",
    ),
)
def create_idea(payload: IdeaCreate, store: ResearchStore = Depends(get_store)) -> ApiEnvelope:
    payload_data = attach_loop_metadata(payload.model_dump(), "idea_pool")
    return envelope(store.create_record("sources", "idea", payload_data))


@router.get(
    "/ideas",
    tags=["method-loop"],
    response_model=ApiEnvelope,
    summary="列出 idea pool 输入",
    openapi_extra=agent_guidance(
        when_to_use="恢复论文、repo、benchmark gap、研究员想法、历史失败和外部观察等假设来源。",
        facts_from="sources backing collection",
        capability_group="method_loop",
        safety_level="read",
        response_contract="返回标准 list envelope data: items,total,limit,offset,sort。",
    ),
)
def list_ideas(
    status: str | None = None,
    q: str = "",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = "-created_at",
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    return query_records(store, "sources", status=status, q=q, limit=limit, offset=offset, sort=sort)


@router.post(
    "/plans",
    tags=["method-loop"],
    response_model=ApiEnvelope,
    summary="创建最小研究计划",
    openapi_extra=agent_guidance(
        when_to_use="把 hypothesis 收敛成最小实验计划，声明唯一变化、验证方式、接受/拒绝标准和结果要求。",
        facts_from="hypothesis, external Runtime planning",
        next_steps=["POST /api/v1/research/sessions", "GET /api/v1/research/design/audit"],
        capability_group="method_loop",
        response_contract="写入 protocols backing collection，并标记 metadata.loop_stage=plan。",
    ),
)
def create_plan(payload: PlanCreate, store: ResearchStore = Depends(get_store)) -> ApiEnvelope:
    payload_data = payload.model_dump()
    if payload_data.get("hypothesis_id"):
        require_record(store.get_record("hypotheses", payload_data["hypothesis_id"]), payload_data["hypothesis_id"])
    payload_data["artifact_requirements"] = payload_data.get("artifact_requirements") or payload_data.get("result_requirements", [])
    payload_data = attach_loop_metadata(payload_data, "plan")
    return envelope(store.create_record("protocols", "plan", payload_data))


@router.get(
    "/plans",
    tags=["method-loop"],
    response_model=ApiEnvelope,
    summary="列出最小研究计划",
    openapi_extra=agent_guidance(
        when_to_use="查找外部 Runtime 已登记的 plan、验证合同和结果要求。",
        facts_from="protocols backing collection",
        capability_group="method_loop",
        safety_level="read",
        response_contract="返回标准 list envelope data: items,total,limit,offset,sort。",
    ),
)
def list_plans(
    status: str | None = None,
    q: str = "",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = "-created_at",
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    return query_records(store, "protocols", status=status, q=q, limit=limit, offset=offset, sort=sort)


@router.post(
    "/results",
    tags=["method-loop"],
    response_model=ApiEnvelope,
    summary="创建结果引用",
    openapi_extra=agent_guidance(
        when_to_use="外部 Runtime 完成实验、benchmark、复现、仿真或文献验证后，登记分数、日志、图表、badcase、commit 或报告引用。",
        facts_from="external Runtime result package",
        next_steps=["POST /api/v1/evidence-records", "POST /api/v1/reviews", "POST /api/v1/decisions"],
        capability_group="method_loop",
        safety="只登记外部 result 引用和轻量 metadata，不保存大文件、原文或 checkpoint。",
        response_contract="写入 artifacts backing collection，并标记 metadata.loop_stage=result。",
    ),
)
def create_result(payload: ResultCreate, store: ResearchStore = Depends(get_store)) -> ApiEnvelope:
    payload_data = payload.model_dump()
    artifact_payload = {
        "artifact_type": payload_data.pop("result_type"),
        "title": payload_data.pop("title"),
        "summary": payload_data.pop("summary"),
        "uri": payload_data.pop("uri"),
        "sha256": payload_data.pop("sha256"),
        "mime_type": payload_data.pop("mime_type"),
        "size_bytes": payload_data.pop("size_bytes"),
        "storage": payload_data.pop("storage"),
        "source_refs": payload_data.pop("source_refs"),
        "payload": {
            "metrics": payload_data.pop("metrics"),
            "artifact_refs": payload_data.pop("artifact_refs"),
            "experiment_id": payload_data.pop("experiment_id"),
            "run_id": payload_data.pop("run_id"),
        },
        "metadata": payload_data.pop("metadata"),
    }
    artifact_payload = attach_loop_metadata(artifact_payload, "result")
    validate_artifact_reference(artifact_payload)
    return envelope(store.create_record("artifacts", "result", artifact_payload))


@router.get(
    "/results",
    tags=["method-loop"],
    response_model=ApiEnvelope,
    summary="列出结果引用",
    openapi_extra=agent_guidance(
        when_to_use="查看分数、日志、图表、badcase、commit、报告或论文草稿等外部结果引用。",
        facts_from="artifacts backing collection",
        capability_group="method_loop",
        safety_level="read",
        response_contract="返回标准 list envelope data: items,total,limit,offset,sort。",
    ),
)
def list_results(
    status: str | None = None,
    q: str = "",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = "-created_at",
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    return query_records(store, "artifacts", status=status, q=q, limit=limit, offset=offset, sort=sort)


@router.get(
    "/lessons",
    tags=["method-loop"],
    response_model=ApiEnvelope,
    summary="列出经验 lessons",
    openapi_extra=agent_guidance(
        when_to_use="按方法论闭环读取已沉淀 lessons。写入仍必须走 experiences curation preview/apply。",
        facts_from="experiences backing collection",
        next_steps=["POST /api/v1/experiences/curation/preview", "POST /api/v1/experiences/curation/apply"],
        capability_group="method_loop",
        safety_level="read",
        safety="只读经验；平台不从 ledger 自动抽取 lesson。",
        response_contract="返回标准 list envelope data: items,total,limit,offset,sort。",
    ),
)
def list_lessons(
    status: str | None = None,
    q: str = "",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = "-created_at",
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    return query_records(store, "experiences", status=status, q=q, limit=limit, offset=offset, sort=sort)


@router.post(
    "/sources",
    tags=["sources"],
    response_model=ApiEnvelope,
    summary="创建资料输入",
    openapi_extra=agent_guidance(
        when_to_use="写入论文、URL、数据集、代码仓库、笔记、artifact 引用或外部 Runtime 输入的引用与摘要。",
        facts_from="external Runtime source parser",
        next_steps=["POST /api/v1/insights", "POST /api/v1/hypotheses"],
        capability_group="source_to_insight",
    ),
)
def create_source(payload: SourceCreate, store: ResearchStore = Depends(get_store)) -> ApiEnvelope:
    return envelope(store.create_record("sources", "source", payload.model_dump()))


@router.get(
    "/sources",
    tags=["sources"],
    response_model=ApiEnvelope,
    summary="列出资料输入",
    openapi_extra=agent_guidance(
        when_to_use="查找已有论文、资料、artifact 引用或外部 Runtime 输入。",
        facts_from="research_sources",
        capability_group="source_to_insight",
        safety_level="read",
    ),
)
def list_sources(
    status: str | None = None,
    q: str = "",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = "-created_at",
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    return query_records(store, "sources", status=None, q=q, limit=limit, offset=offset, sort=sort)


@router.get(
    "/sources/{source_id}",
    tags=["sources"],
    response_model=ApiEnvelope,
    summary="读取资料输入详情",
    openapi_extra=agent_guidance(
        when_to_use="读取单个 source 的 metadata、summary 和 provenance。",
        facts_from="research_sources",
        capability_group="source_to_insight",
        safety_level="read",
    ),
)
def get_source(source_id: str, store: ResearchStore = Depends(get_store)) -> ApiEnvelope:
    return envelope(require_record(store.get_record("sources", source_id), source_id))


@router.post(
    "/insights",
    tags=["insights"],
    response_model=ApiEnvelope,
    summary="创建 insight",
    openapi_extra=agent_guidance(
        when_to_use="外部 Runtime 从 sources 中提炼观点、机制解释、缺口或可验证线索后写入。",
        facts_from="research_sources plus external Runtime analysis",
        next_steps=["POST /api/v1/hypotheses", "POST /api/v1/research/intake"],
        capability_group="source_to_insight",
    ),
)
def create_insight(payload: InsightCreate, store: ResearchStore = Depends(get_store)) -> ApiEnvelope:
    return envelope(store.create_record("insights", "insight", payload.model_dump()))


@router.get(
    "/insights",
    tags=["insights"],
    response_model=ApiEnvelope,
    summary="列出 insights",
    openapi_extra=agent_guidance(
        when_to_use="研究开题或复盘时查找已有 insight。",
        facts_from="research_insights",
        capability_group="source_to_insight",
        safety_level="read",
    ),
)
def list_insights(
    status: str | None = None,
    q: str = "",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = "-created_at",
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    return query_records(store, "insights", status=None, q=q, limit=limit, offset=offset, sort=sort)


@router.post(
    "/hypotheses",
    tags=["insights"],
    response_model=ApiEnvelope,
    summary="创建 hypothesis",
    openapi_extra=agent_guidance(
        when_to_use="把 insight、模糊目标或外部 Runtime 输入转成可验证假设，包含预期效果和接受/拒绝标准。",
        facts_from="research_insights, runtime inputs, external constraints",
        next_steps=["POST /api/v1/research/intake", "POST /api/v1/research/sessions/{session_id}/experiments"],
        capability_group="source_to_insight",
    ),
)
def create_hypothesis(
    payload: HypothesisCreate, store: ResearchStore = Depends(get_store)
) -> ApiEnvelope:
    return envelope(store.create_record("hypotheses", "hypothesis", payload.model_dump()))


@router.get(
    "/hypotheses",
    tags=["insights"],
    response_model=ApiEnvelope,
    summary="列出 hypotheses",
    openapi_extra=agent_guidance(
        when_to_use="查看已预注册或待转入 intake/session 的研究假设。",
        facts_from="research_hypotheses",
        capability_group="source_to_insight",
        safety_level="read",
    ),
)
def list_hypotheses(
    status: str | None = None,
    q: str = "",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = "-created_at",
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    return query_records(store, "hypotheses", status=status, q=q, limit=limit, offset=offset, sort=sort)


@router.post(
    "/research/programs",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="创建研究计划",
    openapi_extra=agent_guidance(
        when_to_use="登记一个长期研究方向、目标、领域和硬约束，作为后续研究问题的上层上下文。",
        facts_from="external Runtime planning, goals, source insights",
        next_steps=["POST /api/v1/research/questions"],
        safety="只登记科研设计，不执行实验、不调模型、不运行 benchmark。",
        capability_group="research_methodology",
    ),
)
def create_research_program(
    payload: ResearchProgramCreate, store: ResearchStore = Depends(get_store)
) -> ApiEnvelope:
    return envelope(store.create_record("research_programs", "program", payload.model_dump()))


@router.get(
    "/research/programs",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="列出研究计划",
    openapi_extra=agent_guidance(
        when_to_use="查找长期研究方向、目标和约束，用于开题或继续研究。",
        facts_from="research_programs",
        capability_group="research_methodology",
        safety_level="read",
    ),
)
def list_research_programs(
    status: str | None = None,
    q: str = "",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = "-created_at",
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    return query_records(store, "research_programs", status=status, q=q, limit=limit, offset=offset, sort=sort)


@router.post(
    "/research/questions",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="创建研究问题",
    openapi_extra=agent_guidance(
        when_to_use="把研究计划或洞察转成可回答问题，记录成功标准和研究动机。",
        facts_from="research_programs, insights, hypotheses, external constraints",
        next_steps=["POST /api/v1/research/method-cards", "POST /api/v1/research/protocols"],
        safety="只登记科研问题，不执行实验。",
        capability_group="research_methodology",
    ),
)
def create_research_question(
    payload: ResearchQuestionCreate, store: ResearchStore = Depends(get_store)
) -> ApiEnvelope:
    if payload.program_id:
        require_record(store.get_record("research_programs", payload.program_id), payload.program_id)
    return envelope(store.create_record("research_questions", "question", payload.model_dump()))


@router.get(
    "/research/questions",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="列出研究问题",
    openapi_extra=agent_guidance(
        when_to_use="查找已登记的可回答问题和成功标准。",
        facts_from="research_questions",
        capability_group="research_methodology",
        safety_level="read",
    ),
)
def list_research_questions(
    status: str | None = None,
    q: str = "",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = "-created_at",
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    return query_records(store, "research_questions", status=status, q=q, limit=limit, offset=offset, sort=sort)


@router.post(
    "/research/method-cards",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="创建方法卡",
    openapi_extra=agent_guidance(
        when_to_use="登记某类研究方法的适用场景、失败模式和所需 artifact，供协议预注册复用。",
        facts_from="external Runtime planning, methodology library",
        next_steps=["POST /api/v1/research/protocols"],
        safety="方法卡是设计记录，不是可执行 workflow 或 DAG。",
        capability_group="research_methodology",
    ),
)
def create_method_card(
    payload: MethodCardCreate, store: ResearchStore = Depends(get_store)
) -> ApiEnvelope:
    return envelope(store.create_record("method_cards", "method", payload.model_dump()))


@router.get(
    "/research/method-cards",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="列出方法卡",
    openapi_extra=agent_guidance(
        when_to_use="查找研究方法、失败模式和所需 artifact。",
        facts_from="method_cards",
        capability_group="research_methodology",
        safety_level="read",
    ),
)
def list_method_cards(
    status: str | None = None,
    q: str = "",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = "-created_at",
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    return query_records(store, "method_cards", status=status, q=q, limit=limit, offset=offset, sort=sort)


@router.post(
    "/research/protocols",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="创建实验协议",
    openapi_extra=agent_guidance(
        when_to_use="预注册实验协议，明确研究问题、方法卡、唯一变化、对照、接受标准和拒绝标准。",
        facts_from="research_questions, method_cards, hypotheses",
        next_steps=["POST /api/v1/research/intake", "POST /api/v1/research/sessions/{session_id}/experiments"],
        safety="protocol 是预注册对象，不是可执行 DAG；执行由外部 Runtime 负责。",
        capability_group="research_methodology",
    ),
)
def create_protocol(payload: ProtocolCreate, store: ResearchStore = Depends(get_store)) -> ApiEnvelope:
    require_record(store.get_record("research_questions", payload.question_id), payload.question_id)
    if payload.method_id:
        require_record(store.get_record("method_cards", payload.method_id), payload.method_id)
    if payload.hypothesis_id:
        require_record(store.get_record("hypotheses", payload.hypothesis_id), payload.hypothesis_id)
    return envelope(store.create_record("protocols", "protocol", payload.model_dump()))


@router.get(
    "/research/protocols",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="列出实验协议",
    openapi_extra=agent_guidance(
        when_to_use="查找已预注册的协议、对照组、接受标准和拒绝标准。",
        facts_from="protocols",
        capability_group="research_methodology",
        safety_level="read",
    ),
)
def list_protocols(
    status: str | None = None,
    q: str = "",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = "-created_at",
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    return query_records(store, "protocols", status=status, q=q, limit=limit, offset=offset, sort=sort)


@router.get(
    "/research/method-templates",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="读取自动化科研方法模板",
    openapi_extra=agent_guidance(
        when_to_use="外部 Runtime 开题、生成方法卡或预注册协议前，选择通用自动化科研设计模板，避免临场拼装实验方法。",
        facts_from="built-in deterministic methodology templates",
        next_steps=[
            "POST /api/v1/research/method-cards",
            "POST /api/v1/research/protocols",
            "GET /api/v1/research/design/audit",
        ],
        capability_group="research_methodology",
        safety_level="read",
        safety="只读方法模板目录，不创建 workflow DAG、不执行实验、不调用模型、不读取外部 Runtime。",
        response_contract="返回 schema、state、templates、recommended_next_actions 和 safety；每个 template 包含 design_questions、required_records、protocol_defaults、artifact_requirements、evidence_expectations、review_gates、next_endpoints。",
    ),
)
def list_research_method_templates() -> ApiEnvelope:
    template_safety = {
        "executes_experiment": False,
        "creates_workflow_dag": False,
        "calls_model": False,
        "reads_external_runtime": False,
    }
    templates = [
        {
            **template,
            "safety": template_safety,
        }
        for template in RESEARCH_METHOD_TEMPLATES
    ]
    return envelope(
        {
            "schema": "autoresearch.method_templates.v1",
            "state": "ready",
            "templates": templates,
            "recommended_next_actions": [
                {
                    "endpoint": "POST /api/v1/research/method-cards",
                    "reason": "将选中的方法模板落成项目内方法卡，补充领域、失败模式和所需 artifact。",
                    "priority": "normal",
                },
                {
                    "endpoint": "POST /api/v1/research/protocols",
                    "reason": "基于模板中的 protocol_defaults 预注册协议，并绑定具体研究问题、方法卡和假设。",
                    "priority": "normal",
                },
                {
                    "endpoint": "GET /api/v1/research/design/audit",
                    "reason": "执行前只读审计研究设计，确认问题、假设和协议满足质量门。",
                    "priority": "normal",
                },
            ],
            "safety": "read_only_methodology_templates_no_execution",
        }
    )


@router.get(
    "/research/design/audit",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="审计研究设计质量门",
    openapi_extra=agent_guidance(
        when_to_use="外部 Runtime 开始实验前，检查研究问题、假设和预注册协议是否可回答、可证伪、可执行和可审计。",
        facts_from="research_questions, hypotheses, protocols",
        next_steps=[
            "POST /api/v1/research/questions",
            "POST /api/v1/hypotheses",
            "POST /api/v1/research/protocols",
            "GET /api/v1/research/readiness",
        ],
        capability_group="research_methodology",
        safety_level="read",
        safety="只读审计研究设计字段，不生成实验、不执行协议、不运行 benchmark。",
        response_contract="返回 state、issue_counts、questions、hypotheses、protocols、recommended_next_actions 和 safety。",
    ),
)
def audit_research_design(
    q: str = "",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = "-created_at",
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    questions = store.query_records(
        "research_questions",
        status=None,
        q=q,
        limit=limit,
        offset=offset,
        sort=sort,
    )["items"]
    hypotheses = store.query_records(
        "hypotheses",
        status=None,
        q=q,
        limit=limit,
        offset=offset,
        sort=sort,
    )["items"]
    protocols = store.query_records(
        "protocols",
        status=None,
        q=q,
        limit=limit,
        offset=offset,
        sort=sort,
    )["items"]
    if q:
        linked_question_ids = {str(question.get("id")) for question in questions if question.get("id")}
        linked_hypothesis_ids = {str(hypothesis.get("id")) for hypothesis in hypotheses if hypothesis.get("id")}
        linked_protocols = store.query_records(
            "protocols",
            status=None,
            q="",
            limit=500,
            offset=0,
            sort=sort,
        )["items"]
        seen_protocol_ids = {str(protocol.get("id")) for protocol in protocols if protocol.get("id")}
        for protocol in linked_protocols:
            protocol_id = str(protocol.get("id") or "")
            if protocol_id in seen_protocol_ids:
                continue
            if str(protocol.get("question_id") or "") in linked_question_ids or str(protocol.get("hypothesis_id") or "") in linked_hypothesis_ids:
                protocols.append(protocol)
                seen_protocol_ids.add(protocol_id)
    return envelope(
        build_research_design_audit(
            questions=questions,
            hypotheses=hypotheses,
            protocols=protocols,
            q=q,
        )
    )


@router.post(
    "/research/intake",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="创建研究任务",
    openapi_extra=agent_guidance(
        when_to_use="外部 Runtime 有待研究问题、下一轮假设、外部目标输入或 benchmark 改进方向。",
        facts_from="runtime goals, insights, hypotheses, runtime events",
        next_steps=["POST /api/v1/research/intake/{item_id}/claim"],
        capability_group="research_intake",
    ),
)
def create_intake(payload: IntakeCreate, store: ResearchStore = Depends(get_store)) -> ApiEnvelope:
    return envelope(store.create_record("intake_items", "intake", payload.model_dump()))


@router.get(
    "/research/intake",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="列出研究任务",
    openapi_extra=agent_guidance(
        when_to_use="外部 Runtime 查找 queued/claimed/running 的研究入口。",
        facts_from="research_intake_items",
        capability_group="research_intake",
        safety_level="read",
    ),
)
def list_intake(
    status: str | None = None,
    q: str = "",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = "-created_at",
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    return query_records(store, "intake_items", status=status, q=q, limit=limit, offset=offset, sort=sort)


@router.post(
    "/research/intake/{item_id}/claim",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="领取研究任务",
    openapi_extra=agent_guidance(
        when_to_use="外部 Runtime 准备处理一个研究任务时先领取，避免多 Runtime 重复推进。",
        facts_from="research_intake_items",
        next_steps=["POST /api/v1/research/intake/{item_id}/start-session"],
        capability_group="research_intake",
    ),
)
def claim_intake(
    item_id: str, operator: str = "external-runtime", store: ResearchStore = Depends(get_store)
) -> ApiEnvelope:
    try:
        return envelope(store.claim_intake(item_id, operator))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"record not found: {item_id}") from exc


@router.post(
    "/research/intake/{item_id}/start-session",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="从研究任务启动 session",
    openapi_extra=agent_guidance(
        when_to_use="任务已领取后，把 intake 转为可写入 events/experiments/artifacts 的 session ledger。",
        facts_from="research_intake_items",
        next_steps=["POST /api/v1/research/sessions/{session_id}/events"],
        capability_group="research_intake",
    ),
)
def start_session_from_intake(
    item_id: str, store: ResearchStore = Depends(get_store)
) -> ApiEnvelope:
    try:
        return envelope(store.start_session_from_intake(item_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"record not found: {item_id}") from exc


@router.post(
    "/research/sessions",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="创建研究 session",
    openapi_extra=agent_guidance(
        when_to_use="开题时记录 memory_context、外部约束、主路径和本轮信息增量。",
        facts_from="experiences/query, sources, insights, external constraints",
        next_steps=["POST /api/v1/research/sessions/{session_id}/events"],
        capability_group="research_session_ledger",
    ),
)
def create_session(payload: SessionCreate, store: ResearchStore = Depends(get_store)) -> ApiEnvelope:
    return envelope(store.create_session(payload.model_dump()))


@router.get(
    "/research/sessions",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="列出研究 sessions",
    openapi_extra=agent_guidance(
        when_to_use="查找历史研究账本、继续未完成任务或为经验维护读取过程材料。",
        facts_from="research_sessions",
        capability_group="research_session_ledger",
        safety_level="read",
    ),
)
def list_sessions(
    status: str | None = None,
    q: str = "",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = "-created_at",
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    return query_records(store, "sessions", status=status, q=q, limit=limit, offset=offset, sort=sort)


@router.get(
    "/research/sessions/{session_id}",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="读取研究 session 详情",
    openapi_extra=agent_guidance(
        when_to_use="读取 session、events、experiments 和 artifacts，用于复盘、继续研究或显式经验维护。",
        facts_from="research_sessions, research_events, research_experiments, research_artifacts",
        capability_group="research_session_ledger",
        safety_level="read",
    ),
)
def get_session(session_id: str, store: ResearchStore = Depends(get_store)) -> ApiEnvelope:
    try:
        return envelope(store.session_detail(session_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"record not found: {session_id}") from exc


@router.post(
    "/research/rounds",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="创建研究轮次",
    openapi_extra=agent_guidance(
        when_to_use="外部 Runtime 为一个新方案或实验轮次登记 proposal、worktree/branch 引用、运行状态和后续追踪引用。",
        facts_from="external Runtime plan, git/worktree references, research sessions",
        next_steps=[
            "PATCH /api/v1/research/rounds/{round_id}",
            "POST /api/v1/research/sessions/{session_id}/experiments",
            "POST /api/v1/evidence-records",
        ],
        safety="平台只保存 worktree、branch、commit、experiment、artifact 和 evidence 引用，不创建 worktree、不提交代码、不读写外部目录。",
        capability_group="research_round_ledger",
    ),
)
def create_research_round(
    payload: ResearchRoundCreate, store: ResearchStore = Depends(get_store)
) -> ApiEnvelope:
    payload_data = payload.model_dump()
    if payload_data.get("session_id"):
        require_record(store.get_record("sessions", payload_data["session_id"]), payload_data["session_id"])
    validate_research_round(payload_data)
    return envelope(store.create_record("research_rounds", "round", payload_data))


@router.get(
    "/research/rounds",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="列出研究轮次",
    openapi_extra=agent_guidance(
        when_to_use="外部 Runtime 查询方案轮次、worktree/branch、commit、实验、artifact、证据和决策引用。",
        facts_from="research_rounds",
        capability_group="research_round_ledger",
        safety_level="read",
    ),
)
def list_research_rounds(
    status: str | None = None,
    q: str = "",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = "-created_at",
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    return query_records(store, "research_rounds", status=status, q=q, limit=limit, offset=offset, sort=sort)


@router.get(
    "/research/rounds/{round_id}",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="读取研究轮次追踪包",
    openapi_extra=agent_guidance(
        when_to_use="外部 Runtime 继续某一轮方案前，恢复该轮 worktree、commit、实验、artifact、证据和决策引用。",
        facts_from="research_rounds, research_sessions, research_experiments, artifacts, evidence_records, decisions",
        next_steps=[
            "PATCH /api/v1/research/rounds/{round_id}",
            "POST /api/v1/evidence-records",
            "POST /api/v1/decisions",
        ],
        safety="只读取 round 已登记引用并解析平台内记录，不执行 git、不运行实验、不推断隐藏关系。",
        capability_group="research_round_ledger",
        safety_level="read",
        response_contract="返回 round、session、trace、recommended_next_actions；缺失引用进入 warnings 和 trace.unresolved_refs。",
    ),
)
def get_research_round(round_id: str, store: ResearchStore = Depends(get_store)) -> ApiEnvelope:
    round_record = require_record(store.get_record("research_rounds", round_id), round_id)
    detail = build_research_round_detail(store, round_record)
    unresolved_count = len(detail["trace"]["unresolved_refs"])
    warnings = [f"unresolved round refs: {unresolved_count}"] if unresolved_count else []
    return envelope(detail, warnings)


@router.patch(
    "/research/rounds/{round_id}",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="更新研究轮次",
    openapi_extra=agent_guidance(
        when_to_use="外部 Runtime 完成实现、提交、实验、证据或决策后回填本轮追踪引用和 retrospective。",
        facts_from="external Runtime git/worktree, research_experiments, artifacts, evidence_records, decisions",
        next_steps=["POST /api/v1/evidence-records", "POST /api/v1/decisions"],
        safety="只保存引用和状态，不执行 git、实验或文件系统操作。",
        capability_group="research_round_ledger",
    ),
)
def patch_research_round(
    round_id: str, payload: ResearchRoundPatch, store: ResearchStore = Depends(get_store)
) -> ApiEnvelope:
    try:
        existing = require_record(store.get_record("research_rounds", round_id), round_id)
        payload_data = payload.model_dump()
        candidate = {
            **existing,
            **{key: value for key, value in payload_data.items() if value is not None},
        }
        validate_research_round(candidate)
        return envelope(store.patch_record("research_rounds", round_id, payload_data))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"record not found: {round_id}") from exc


@router.post(
    "/research/sessions/{session_id}/events",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="追加研究事件",
    openapi_extra=agent_guidance(
        when_to_use="记录 observation、decision、tool_run、外部指令、runtime_event 或 blocker。",
        facts_from="external Runtime event stream",
        next_steps=["POST /api/v1/research/sessions/{session_id}/experiments"],
        capability_group="research_session_ledger",
    ),
)
def add_event(
    session_id: str, payload: EventCreate, store: ResearchStore = Depends(get_store)
) -> ApiEnvelope:
    try:
        return envelope(
            store.add_session_child(
                collection="events",
                prefix="event",
                session_id=session_id,
                payload=payload.model_dump(),
            )
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"record not found: {session_id}") from exc


@router.get(
    "/research/events",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="列出研究过程事件",
    openapi_extra=agent_guidance(
        when_to_use="跨 session 查询 observation、decision、tool_run、外部指令、runtime_event 和 blocker。",
        facts_from="research_events",
        capability_group="research_audit",
        safety_level="read",
    ),
)
def list_events(
    q: str = "",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = "-created_at",
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    return query_records(store, "events", status=None, q=q, limit=limit, offset=offset, sort=sort)


@router.get(
    "/research/context",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="读取研究上下文恢复包",
    openapi_extra=agent_guidance(
        when_to_use="外部 Runtime 开题或恢复研究前，按关键词读取已有资料、假设、过程、artifact、证据、风险和建议下一步。",
        facts_from="sources, insights, hypotheses, sessions, events, experiments, artifacts, evidence_records, reviews, decisions",
        next_steps=[
            "POST /api/v1/sources",
            "POST /api/v1/research/protocols",
            "POST /api/v1/evidence-records",
            "POST /api/v1/reviews",
            "POST /api/v1/decisions",
        ],
        capability_group="research_audit",
        safety_level="read",
        response_contract="返回 query、claim、state、counts、sections、evidence_summary、risk_flags 和 recommended_next_actions。",
    ),
)
def research_context(
    query: str = Query(..., min_length=1),
    claim: str = "",
    limit: int = Query(10, ge=1, le=50),
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    return envelope(build_research_context(store, query=query, claim=claim, limit=limit))


@router.get(
    "/research/readiness",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="读取研究就绪检查",
    openapi_extra=agent_guidance(
        when_to_use="外部 Runtime 在执行、审查、决策或经验维护前，检查上下文、轮次追踪、实验预注册和证据是否足够。",
        facts_from="research_context, research_rounds, research_experiments, artifacts, evidence_records, decisions",
        next_steps=[
            "GET /api/v1/research/context",
            "GET /api/v1/research/rounds/{round_id}",
            "POST /api/v1/evidence-records",
            "POST /api/v1/decisions",
        ],
        safety="只读 preflight，不执行实验、不调用模型、不创建 workflow DAG。",
        capability_group="research_audit",
        safety_level="read",
        response_contract="返回 state、checks、blocking_gaps、warning_gaps、context、round_trace、warnings 和 recommended_next_actions。",
    ),
)
def research_readiness(
    query: str = Query(..., min_length=1),
    claim: str = "",
    round_id: str = "",
    stage: str = "before_experiment",
    limit: int = Query(10, ge=1, le=50),
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    return envelope(
        build_research_readiness(
            store,
            query=query,
            claim=claim,
            round_id=round_id,
            stage=stage,
            limit=limit,
        )
    )


@router.get(
    "/research/audit/export",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="导出研究审计包",
    openapi_extra=agent_guidance(
        when_to_use="外部 Runtime 需要把某个主题、session 或 round 的上下文、追踪包和质量门打包用于交接、复现或开源审计。",
        facts_from="research_context, research_sessions, research_rounds, artifacts, reviews",
        next_steps=[
            "GET /api/v1/research/context",
            "GET /api/v1/research/rounds/{round_id}",
            "GET /api/v1/artifacts/audit",
            "GET /api/v1/reviews/audit",
        ],
        capability_group="research_audit",
        safety_level="read",
        safety="只读导出平台内账本和 metadata，不访问外部 artifact URI、不读取外部 Runtime 工作目录、不执行实验。",
        response_contract="返回 audit bundle manifest、filters、context、session_ledger、round_trace、artifact_audit、review_audit、reproducibility、integrity、recommended_next_actions 和 safety。",
    ),
)
def export_research_audit_bundle(
    query: str = Query(..., min_length=1),
    claim: str = "",
    session_id: str = "",
    round_id: str = "",
    limit: int = Query(20, ge=1, le=100),
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    try:
        return envelope(
            build_research_audit_export(
                store,
                query=query,
                claim=claim,
                session_id=session_id,
                round_id=round_id,
                limit=limit,
            )
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"record not found: {exc.args[0]}") from exc


@router.post(
    "/research/sessions/{session_id}/experiments",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="预注册实验",
    openapi_extra=agent_guidance(
        when_to_use="每个正式实验先写 hypothesis、expected_effect、acceptance_criteria 和 rejection_criteria。",
        facts_from="research hypothesis and external constraints",
        next_steps=["PATCH /api/v1/research/sessions/{session_id}/experiments/{experiment_id}"],
        capability_group="research_session_ledger",
    ),
)
def add_experiment(
    session_id: str, payload: ExperimentCreate, store: ResearchStore = Depends(get_store)
) -> ApiEnvelope:
    try:
        return envelope(
            store.add_session_child(
                collection="experiments",
                prefix="experiment",
                session_id=session_id,
                payload=payload.model_dump(),
            )
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"record not found: {session_id}") from exc


@router.get(
    "/research/experiments",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="列出研究实验",
    openapi_extra=agent_guidance(
        when_to_use="跨 session 查询预注册实验、完成结果、失败尝试、阻塞和降级实验。",
        facts_from="research_experiments",
        capability_group="research_audit",
        safety_level="read",
    ),
)
def list_experiments(
    status: str | None = None,
    q: str = "",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = "-created_at",
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    return query_records(store, "experiments", status=status, q=q, limit=limit, offset=offset, sort=sort)


@router.patch(
    "/research/sessions/{session_id}/experiments/{experiment_id}",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="更新实验结果",
    openapi_extra=agent_guidance(
        when_to_use="外部 Runtime 完成实验、失败、阻塞或降级后回填结果、metrics 和 artifact 引用。",
        facts_from="external Runtime experiment result",
        next_steps=["POST /api/v1/research/sessions/{session_id}/artifacts"],
        capability_group="research_session_ledger",
    ),
)
def patch_experiment(
    session_id: str,
    experiment_id: str,
    payload: ExperimentPatch,
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    experiment = store.get_record("experiments", experiment_id)
    if not experiment or experiment.get("session_id") != session_id:
        raise HTTPException(status_code=404, detail=f"record not found: {experiment_id}")
    return envelope(store.patch_record("experiments", experiment_id, payload.model_dump()))


@router.post(
    "/research/sessions/{session_id}/artifacts",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="登记研究 artifact",
    openapi_extra=agent_guidance(
        when_to_use="登记 report、table、chart、log、dataset_ref、code_patch、benchmark_result 或其他外部 artifact 引用。",
        facts_from="external Runtime artifacts",
        next_steps=["POST /api/v1/research/sessions/{session_id}/close"],
        capability_group="research_session_ledger",
    ),
)
def add_artifact(
    session_id: str, payload: ArtifactCreate, store: ResearchStore = Depends(get_store)
) -> ApiEnvelope:
    artifact_payload = payload.model_dump()
    validate_artifact_reference(artifact_payload)
    try:
        return envelope(
            store.add_session_child(
                collection="artifacts",
                prefix="artifact",
                session_id=session_id,
                payload=artifact_payload,
            )
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"record not found: {session_id}") from exc


@router.get(
    "/artifacts/audit",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="审计成果引用元数据",
    openapi_extra=agent_guidance(
        when_to_use="外部 Runtime 在把 artifact 用作 evidence、review 或 decision 前，检查 URI、hash、大小、存储和摘要是否足够可审计。",
        facts_from="research_artifacts",
        next_steps=["POST /api/v1/research/sessions/{session_id}/artifacts", "POST /api/v1/evidence-records"],
        capability_group="artifact_registry",
        safety_level="read",
        safety="只读取平台内 artifact metadata，不访问 URI、不读取外部存储、不下载大文件。",
        response_contract="返回 state、issue_counts、artifact_ids_with_issues、items、recommended_next_actions 和 metadata_only safety。",
    ),
)
def audit_artifacts(
    session_id: str | None = None,
    q: str = "",
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = "-created_at",
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    records = store.query_records("artifacts", status=None, q=q, limit=limit, offset=offset, sort=sort)["items"]
    if session_id:
        records = [record for record in records if str(record.get("session_id") or "") == session_id]
    return envelope(build_artifact_audit(records, q=q, session_id=session_id))


@router.get(
    "/artifacts",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="列出成果引用",
    openapi_extra=agent_guidance(
        when_to_use="跨 session 查询外部 artifact 引用、结果、日志、数据集和 benchmark 输出索引。",
        facts_from="research_artifacts",
        capability_group="artifact_registry",
        safety_level="read",
        safety="只读取 artifact 引用和摘要，不读取外部存储中的大文件或原文。",
    ),
)
def list_artifacts(
    status: str | None = None,
    q: str = "",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = "-created_at",
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    return query_records(store, "artifacts", status=None, q=q, limit=limit, offset=offset, sort=sort)


@router.post(
    "/research/sessions/{session_id}/close",
    tags=["research"],
    response_model=ApiEnvelope,
    summary="关闭研究 session",
    openapi_extra=agent_guidance(
        when_to_use="研究收尾，写入 failed_attempts、platform_gaps、validated_lessons 和 next_agent_one_liner。",
        facts_from="research ledger and external Runtime closeout",
        next_steps=["POST /api/v1/experiences/curation/preview"],
        safety="不会自动创建长期经验；经验必须显式 curation。",
        capability_group="research_session_ledger",
    ),
)
def close_session(
    session_id: str, payload: SessionClose, store: ResearchStore = Depends(get_store)
) -> ApiEnvelope:
    try:
        return envelope(store.close_session(session_id, payload.model_dump()))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"record not found: {session_id}") from exc


@router.post(
    "/benchmarks",
    tags=["benchmarks"],
    response_model=ApiEnvelope,
    summary="创建 benchmark suite",
    openapi_extra=agent_guidance(
        when_to_use="登记 Agent 记忆、AI for Science、算法或架构创新实验的固定评测任务集。",
        facts_from="Runtime benchmark definition or external benchmark specification",
        next_steps=["POST /api/v1/benchmark-runs"],
        capability_group="benchmark_registry",
    ),
)
def create_benchmark(
    payload: BenchmarkCreate, store: ResearchStore = Depends(get_store)
) -> ApiEnvelope:
    return envelope(store.create_record("benchmarks", "benchmark", payload.model_dump()))


@router.get(
    "/benchmarks/audit",
    tags=["benchmarks"],
    response_model=ApiEnvelope,
    summary="审计 benchmark suite 合同",
    openapi_extra=agent_guidance(
        when_to_use="外部 Runtime 准备接入或运行 benchmark 前，检查 suite 是否包含 adapter、输入、输出、指标和 artifact 要求。",
        facts_from="benchmarks",
        next_steps=["POST /api/v1/benchmarks", "POST /api/v1/benchmark-runs"],
        capability_group="benchmark_registry",
        safety_level="read",
        safety="只审计 benchmark suite 元数据，不执行评测、不读取外部数据集、不调用模型。",
    ),
)
def audit_benchmarks(
    q: str = "",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = "-created_at",
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    records = store.query_records("benchmarks", status=None, q=q, limit=limit, offset=offset, sort=sort)["items"]
    return envelope(build_benchmark_audit(records, q=q))


@router.get(
    "/benchmarks",
    tags=["benchmarks"],
    response_model=ApiEnvelope,
    summary="列出 benchmark suites",
    openapi_extra=agent_guidance(
        when_to_use="查找可运行的固定评测任务集；平台只列定义，不执行。",
        facts_from="benchmarks",
        capability_group="benchmark_registry",
        safety_level="read",
    ),
)
def list_benchmarks(
    status: str | None = None,
    q: str = "",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = "-created_at",
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    return query_records(store, "benchmarks", status=status, q=q, limit=limit, offset=offset, sort=sort)


@router.post(
    "/benchmark-runs",
    tags=["benchmarks"],
    response_model=ApiEnvelope,
    summary="创建 benchmark run",
    openapi_extra=agent_guidance(
        when_to_use="外部 Runtime 开始或完成 benchmark 后提交 run 状态、score、artifact 和 provenance。",
        facts_from="external Runtime benchmark runner",
        next_steps=["PATCH /api/v1/benchmark-runs/{run_id}", "POST /api/v1/evidence-records"],
        capability_group="benchmark_registry",
    ),
)
def create_benchmark_run(
    payload: BenchmarkRunCreate, store: ResearchStore = Depends(get_store)
) -> ApiEnvelope:
    payload_data = payload.model_dump()
    validate_benchmark_completion(payload_data)
    return envelope(store.create_record("benchmark_runs", "benchrun", payload_data))


@router.get(
    "/benchmark-runs",
    tags=["benchmarks"],
    response_model=ApiEnvelope,
    summary="列出 benchmark runs",
    openapi_extra=agent_guidance(
        when_to_use="查看外部 Runtime 已提交的 benchmark run、score、状态和 artifact 引用。",
        facts_from="benchmark_runs",
        capability_group="benchmark_registry",
        safety_level="read",
    ),
)
def list_benchmark_runs(
    status: str | None = None,
    q: str = "",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = "-created_at",
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    return query_records(store, "benchmark_runs", status=status, q=q, limit=limit, offset=offset, sort=sort)


@router.get(
    "/benchmark-runs/compare",
    tags=["benchmarks"],
    response_model=ApiEnvelope,
    summary="对比 benchmark runs",
    openapi_extra=agent_guidance(
        when_to_use="外部 Runtime 已提交多个 benchmark run 后，只读比较分数、状态、最佳 run 和证据准备缺口。",
        facts_from="benchmarks, benchmark_runs",
        next_steps=["PATCH /api/v1/benchmark-runs/{run_id}", "POST /api/v1/evidence-records", "GET /api/v1/reviews/audit"],
        capability_group="benchmark_registry",
        safety_level="read",
        safety="只读汇总平台内 run metadata，不执行 benchmark、不读取 artifact URI、不调用模型。",
        response_contract="返回 schema、state、benchmark_id、metric、direction、status_counts、best_run、score_range、ranked_runs、items、issue_counts、run_ids_with_issues、recommended_next_actions 和 safety。",
    ),
)
def compare_benchmark_runs(
    benchmark_id: str,
    metric: str | None = None,
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    benchmark = require_record(store.get_record("benchmarks", benchmark_id), benchmark_id)
    runs = [run for run in store.list_records("benchmark_runs") if run.get("benchmark_id") == benchmark_id]
    return envelope(build_benchmark_run_comparison(benchmark=benchmark, runs=runs, metric=metric))


@router.patch(
    "/benchmark-runs/{run_id}",
    tags=["benchmarks"],
    response_model=ApiEnvelope,
    summary="更新 benchmark run",
    openapi_extra=agent_guidance(
        when_to_use="外部 Runtime 回填 benchmark 完成、失败、阻塞或降级状态。",
        facts_from="external Runtime benchmark runner",
        next_steps=["POST /api/v1/evidence-records", "POST /api/v1/research/sessions/{session_id}/artifacts"],
        capability_group="benchmark_registry",
    ),
)
def patch_benchmark_run(
    run_id: str, payload: BenchmarkRunPatch, store: ResearchStore = Depends(get_store)
) -> ApiEnvelope:
    try:
        existing = require_record(store.get_record("benchmark_runs", run_id), run_id)
        payload_data = payload.model_dump()
        candidate = {
            **existing,
            **{key: value for key, value in payload_data.items() if value is not None},
        }
        validate_benchmark_completion(candidate)
        return envelope(store.patch_record("benchmark_runs", run_id, payload_data))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"record not found: {run_id}") from exc


@router.post(
    "/evidence-records",
    tags=["evidence"],
    response_model=ApiEnvelope,
    summary="创建证据记录",
    openapi_extra=agent_guidance(
        when_to_use="将 benchmark、experiment、artifact、source 或 review 与 claim 绑定，记录支持、反证、不确定、复现或复现失败。",
        facts_from="sources, research_experiments, benchmark_runs, artifacts, reviews",
        next_steps=["POST /api/v1/reviews", "POST /api/v1/decisions"],
        capability_group="evidence_records",
    ),
)
def create_evidence_record(payload: EvidenceRecordCreate, store: ResearchStore = Depends(get_store)) -> ApiEnvelope:
    payload_data = payload.model_dump()
    validate_evidence_record(payload_data)
    return envelope(store.create_record("evidence_records", "evidence", payload_data))


@router.get(
    "/evidence-records/summary",
    tags=["evidence"],
    response_model=ApiEnvelope,
    summary="读取科研主张证据概览",
    openapi_extra=agent_guidance(
        when_to_use="外部 Runtime 需要在 review 或 decision 前检查某个科研主张的支持、反证、不确定和复现证据是否冲突。",
        facts_from="evidence_records",
        next_steps=["POST /api/v1/evidence-records", "POST /api/v1/reviews", "POST /api/v1/decisions"],
        capability_group="evidence_records",
        safety_level="read",
        response_contract="返回主张、total、stance/confidence 计数、evidence_ids、limitations、coverage、quality_gaps、replication_plan、state 和 recommended_next_action。",
    ),
)
def evidence_summary(
    claim: str = Query(..., min_length=1),
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    records = store.query_records(
        "evidence_records",
        status="completed",
        q=claim,
        limit=500,
        offset=0,
        sort="-created_at",
    )["items"]
    return envelope(summarize_evidence_claim(records, claim))


@router.get(
    "/evidence-records",
    tags=["evidence"],
    response_model=ApiEnvelope,
    summary="列出证据记录",
    openapi_extra=agent_guidance(
        when_to_use="按关键词、状态、分页和排序审计支持、反证、不确定、复现或复现失败记录。",
        facts_from="evidence_records",
        capability_group="evidence_records",
        safety_level="read",
    ),
)
def list_evidence_records(
    status: str | None = None,
    q: str = "",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = "-created_at",
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    return query_records(store, "evidence_records", status=status, q=q, limit=limit, offset=offset, sort=sort)


@router.post(
    "/reviews",
    tags=["reviews"],
    response_model=ApiEnvelope,
    summary="创建审查事件",
    openapi_extra=agent_guidance(
        when_to_use="自动 critic、外部 Runtime 或必要的人类复核对 evidence、experiment、benchmark run 或 experience 做审查和降级判断。",
        facts_from="evidence_records, critic Runtime, external Runtime review",
        capability_group="review_events",
    ),
)
def create_review(payload: ReviewCreate, store: ResearchStore = Depends(get_store)) -> ApiEnvelope:
    payload_data = payload.model_dump()
    payload_data.setdefault("status", payload_data["verdict"])
    return envelope(store.create_record("reviews", "review", payload_data))


@router.get(
    "/reviews/audit",
    tags=["reviews"],
    response_model=ApiEnvelope,
    summary="审计审查事件质量门",
    openapi_extra=agent_guidance(
        when_to_use="外部 Runtime 在写 decision 前，检查 review 是否绑定证据、审查来源、说明和风险字段。",
        facts_from="review_events",
        next_steps=["POST /api/v1/reviews", "POST /api/v1/decisions"],
        capability_group="review_events",
        safety_level="read",
        safety="只读取 review ledger，不调用 critic、不运行模型、不自动接受结论。",
        response_contract="返回 state、issue_counts、review_ids_with_issues、items、recommended_next_actions 和 ledger_only safety。",
    ),
)
def audit_reviews(
    status: str | None = None,
    q: str = "",
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = "-created_at",
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    records = store.query_records("reviews", status=status, q=q, limit=limit, offset=offset, sort=sort)["items"]
    return envelope(build_review_audit(records, q=q))


@router.get(
    "/reviews",
    tags=["reviews"],
    response_model=ApiEnvelope,
    summary="列出审查事件",
    openapi_extra=agent_guidance(
        when_to_use="审计自动 critic、外部 Runtime 或必要的人类复核对 evidence、experiment、benchmark run 或 experience 的审查结论。",
        facts_from="review_events",
        capability_group="review_events",
        safety_level="read",
    ),
)
def list_reviews(
    status: str | None = None,
    q: str = "",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = "-created_at",
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    return query_records(store, "reviews", status=status, q=q, limit=limit, offset=offset, sort=sort)


@router.post(
    "/decisions",
    tags=["reviews"],
    response_model=ApiEnvelope,
    summary="创建科研决策",
    openapi_extra=agent_guidance(
        when_to_use="将 review、benchmark、experiment、artifact 或 hypothesis 的证据转成可审计科研决策。",
        facts_from="evidence_records, reviews, benchmark_runs, research_experiments, artifacts",
        next_steps=["POST /api/v1/experiences/curation/preview"],
        capability_group="decision_records",
    ),
)
def create_decision(payload: DecisionCreate, store: ResearchStore = Depends(get_store)) -> ApiEnvelope:
    payload_data = payload.model_dump()
    validate_decision_record(payload_data)
    return envelope(store.create_record("decisions", "decision", payload_data))


@router.get(
    "/decisions",
    tags=["reviews"],
    response_model=ApiEnvelope,
    summary="列出科研决策",
    openapi_extra=agent_guidance(
        when_to_use="审计已接受、拒绝、继续、阻塞、替代或归档的科研判断。",
        facts_from="decision_records",
        capability_group="decision_records",
        safety_level="read",
    ),
)
def list_decisions(
    status: str | None = None,
    q: str = "",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = "-created_at",
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    return query_records(store, "decisions", status=status, q=q, limit=limit, offset=offset, sort=sort)


@router.post(
    "/experiences/query",
    tags=["experiences"],
    response_model=ApiEnvelope,
    summary="查询长期经验",
    openapi_extra=agent_guidance(
        when_to_use="研究开题前检索历史经验、失败路线、已验证 lessons 和 next-agent one-liner。",
        facts_from="experiences",
        next_steps=["POST /api/v1/research/sessions"],
        capability_group="experience_curation",
    ),
)
def query_experiences(
    payload: ExperienceQuery, store: ResearchStore = Depends(get_store)
) -> ApiEnvelope:
    return envelope(store.query_experiences(payload.query, payload.topics, payload.limit))


@router.post(
    "/experiences/curation/preview",
    tags=["experiences"],
    response_model=ApiEnvelope,
    summary="预检经验维护 payload",
    openapi_extra=agent_guidance(
        when_to_use="外部 Runtime 从 ledger、artifact、evidence、review 和 decision 显式生成经验维护 payload 后先预检。",
        facts_from="external Runtime curation payload",
        next_steps=["POST /api/v1/experiences/curation/apply"],
        capability_group="experience_curation",
        safety_level="read",
        safety="只解析平台内 source_refs，不自动抽取经验、不读取外部存储、不执行 Runtime 动作。",
        response_contract="返回 accepted、warnings、source_trace、governance_gaps、recommended_next_actions、safety 和原始 payload；unresolved_source_refs 是阻塞缺口。",
    ),
)
def preview_experience_curation(
    payload: ExperienceCurationRequest, store: ResearchStore = Depends(get_store)
) -> ApiEnvelope:
    preview = store.preview_curation(payload.model_dump())
    return envelope(preview, preview["warnings"])


@router.post(
    "/experiences/curation/apply",
    tags=["experiences"],
    response_model=ApiEnvelope,
    summary="应用经验维护 payload",
    openapi_extra=agent_guidance(
        when_to_use="curation preview 后，由外部 Runtime 写入 candidate/rejected/superseded/topic summary；可选附带外部审批 provenance。",
        facts_from="external Runtime curation payload",
        next_steps=["GET /api/v1/experiences"],
        capability_group="experience_curation",
        safety="只写入显式 curation payload；存在阻塞型 source_refs 治理缺口时返回 422。",
        response_contract="返回写入后的 experience、warnings、source_trace 和 governance_gaps。",
    ),
)
def apply_experience_curation(
    payload: ExperienceCurationRequest, store: ResearchStore = Depends(get_store)
) -> ApiEnvelope:
    try:
        applied = store.apply_curation(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"record not found: {exc.args[0]}") from exc
    return envelope(applied, applied["warnings"])


@router.get(
    "/experiences",
    tags=["experiences"],
    response_model=ApiEnvelope,
    summary="列出长期经验",
    openapi_extra=agent_guidance(
        when_to_use="浏览长期经验库。",
        facts_from="experiences",
        capability_group="experience_curation",
        safety_level="read",
    ),
)
def list_experiences(
    status: str | None = None,
    q: str = "",
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = "-created_at",
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    return query_records(store, "experiences", status=status, q=q, limit=limit, offset=offset, sort=sort)


@router.get(
    "/experiences/{experience_id}",
    tags=["experiences"],
    response_model=ApiEnvelope,
    summary="读取经验详情",
    openapi_extra=agent_guidance(
        when_to_use="读取单条长期经验及其 evidence_refs、scope 和 curation 来源。",
        facts_from="experiences",
        capability_group="experience_curation",
        safety_level="read",
    ),
)
def get_experience(experience_id: str, store: ResearchStore = Depends(get_store)) -> ApiEnvelope:
    return envelope(require_record(store.get_record("experiences", experience_id), experience_id))


@router.get(
    "/experience-topics",
    tags=["experiences"],
    response_model=ApiEnvelope,
    summary="列出经验专题",
    openapi_extra=agent_guidance(
        when_to_use="浏览长期经验专题摘要；专题摘要必须由外部 Runtime 显式维护，可附带外部审批 provenance。",
        facts_from="experience_topics",
        capability_group="experience_curation",
        safety_level="read",
    ),
)
def list_experience_topics(store: ResearchStore = Depends(get_store)) -> ApiEnvelope:
    return envelope(store.list_records("experience_topics"))


@router.put(
    "/experience-topics/{topic_id}/summary",
    tags=["experiences"],
    response_model=ApiEnvelope,
    summary="维护经验专题摘要",
    openapi_extra=agent_guidance(
        when_to_use="外部 Runtime 审阅经验集合后，显式写入某个专题摘要；可选附带外部审批 provenance。",
        facts_from="external Runtime curation payload, experiences",
        capability_group="experience_curation",
    ),
)
def update_experience_topic_summary(
    topic_id: str,
    payload: ExperienceTopicSummaryUpdate,
    store: ResearchStore = Depends(get_store),
) -> ApiEnvelope:
    existing = store.get_record("experience_topics", topic_id)
    data = {"id": topic_id, **payload.model_dump()}
    if existing:
        return envelope(store.patch_record("experience_topics", topic_id, data))
    return envelope(store.create_record("experience_topics", "topic", data))

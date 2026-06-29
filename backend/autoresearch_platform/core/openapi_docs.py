"""OpenAPI metadata for external Runtime discovery."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI


OPENAPI_DESCRIPTION = """
AutoResearch Platform 是外部科研 Runtime 的 REST/OpenAPI 事实源。

平台负责保存资料、insight、任务、session ledger、实验、artifact、benchmark run、
review、通用 Runtime 事件和长期经验。模型调用、benchmark 执行、agent loop、
训练和评测由外部 Runtime 负责。
"""

OPENAPI_TAGS = [
    {"name": "capabilities", "description": "外部 Runtime 能力发现入口。"},
    {"name": "system", "description": "平台只读状态。"},
    {"name": "sources", "description": "论文、URL、数据集、代码仓库、笔记、artifact 引用和外部 Runtime 输入。"},
    {"name": "insights", "description": "从资料产生的 insight 与 hypothesis。"},
    {"name": "research", "description": "研究任务队列、session ledger、实验、事件、artifact 和收尾。"},
    {"name": "benchmarks", "description": "benchmark suite 与外部 Runtime 提交的 run 结果。"},
    {"name": "evidence", "description": "证据质量、支持/反证、复现和限制记录。"},
    {"name": "reviews", "description": "自动 critic、外部 Runtime 或人工复核产生的审查事件。"},
    {"name": "experiences", "description": "长期经验查询和显式 curation。"},
]

AGENT_CAPABILITIES: list[dict[str, Any]] = [
    {
        "id": "platform_readiness",
        "name": "平台部署就绪检查",
        "primary_endpoint": "GET /api/v1/system/readiness",
        "next_endpoints": [
            "GET /api/v1/agent/onboarding",
            "GET /api/v1/system/security",
            "GET /api/v1/system/status",
            "GET /api/v1/system/audit-log",
            "GET /api/v1/openapi.json",
        ],
        "facts_from": "store health, alembic migration contract, security settings, OpenAPI metadata",
        "when_to_use": "外部 Runtime 接入、部署发布或切换持久化配置前，确认平台 store、schema、安全和审计边界是否就绪。",
        "safety": "只读平台配置和迁移合同，不访问外部 Runtime、不读取 artifact URI、不执行迁移。",
    },
    {
        "id": "source_to_insight",
        "name": "资料到 insight",
        "primary_endpoint": "POST /api/v1/sources",
        "next_endpoints": ["POST /api/v1/insights", "POST /api/v1/hypotheses"],
        "facts_from": "research_sources, research_insights",
        "when_to_use": "外部 Runtime 已解析论文、网页、数据集、代码仓库或外部目标输入，需要写入可追溯输入与 insight。",
        "safety": "平台只保存引用、摘要和 provenance，不保存大 PDF、音频、视频或模型文件。",
    },
    {
        "id": "research_intake",
        "name": "研究任务队列",
        "primary_endpoint": "POST /api/v1/research/intake",
        "next_endpoints": [
            "POST /api/v1/research/intake/{item_id}/claim",
            "POST /api/v1/research/intake/{item_id}/start-session",
        ],
        "facts_from": "research_intake_items",
        "when_to_use": "外部 Runtime 需要登记待验证研究问题、下一轮假设、模糊目标输入或 benchmark 改进方向。",
        "safety": "领取任务不代表执行实验；执行仍由外部 Runtime 负责。",
    },
    {
        "id": "research_methodology",
        "name": "科研方法论注册",
        "primary_endpoint": "POST /api/v1/research/programs",
        "next_endpoints": [
            "POST /api/v1/research/questions",
            "GET /api/v1/research/method-templates",
            "POST /api/v1/research/method-cards",
            "POST /api/v1/research/protocols",
            "GET /api/v1/research/design/audit",
            "POST /api/v1/research/intake",
        ],
        "facts_from": "research_programs, research_questions, method_cards, protocols",
        "when_to_use": "将长期研究计划、可回答问题、方法卡和实验协议登记为可审计事实，并在执行前检查设计质量门。",
        "safety": "只登记和审计科研设计与约束，不执行实验、不调模型、不运行 benchmark。",
    },
    {
        "id": "research_session_ledger",
        "name": "科研账本",
        "primary_endpoint": "POST /api/v1/research/sessions",
        "next_endpoints": [
            "POST /api/v1/research/sessions/{session_id}/events",
            "POST /api/v1/research/sessions/{session_id}/experiments",
            "POST /api/v1/research/sessions/{session_id}/artifacts",
            "POST /api/v1/research/sessions/{session_id}/close",
        ],
        "facts_from": "research_sessions, research_events, research_experiments, research_artifacts",
        "when_to_use": "需要记录研究过程、预注册假设、实验结果、失败路线和收尾复盘。",
        "safety": "close session 不会自动创建长期经验；经验必须走 curation preview/apply。",
    },
    {
        "id": "research_round_ledger",
        "name": "研究轮次留痕",
        "primary_endpoint": "POST /api/v1/research/rounds",
        "next_endpoints": [
            "GET /api/v1/research/rounds",
            "GET /api/v1/research/rounds/{round_id}",
            "PATCH /api/v1/research/rounds/{round_id}",
            "POST /api/v1/evidence-records",
        ],
        "facts_from": "research_rounds, git/worktree references, research_experiments, artifacts, evidence_records",
        "when_to_use": "外部 Runtime 需要为每一轮方案、worktree/branch、commit、实验、artifact、证据和决策保留可审计引用。",
        "safety": "平台只保存引用和状态，不创建 worktree、不提交代码、不读写外部 Runtime 工作目录。",
    },
    {
        "id": "research_audit",
        "name": "过程与实验审计",
        "primary_endpoint": "GET /api/v1/research/events",
        "next_endpoints": [
            "GET /api/v1/research/context",
            "GET /api/v1/research/readiness",
            "GET /api/v1/research/audit/export",
            "GET /api/v1/research/experiments",
            "GET /api/v1/artifacts",
        ],
        "facts_from": "research_events, research_experiments, research_artifacts, research_rounds, evidence_records, reviews",
        "when_to_use": "外部 Runtime 需要跨 session 恢复过程历史、失败尝试、阻塞原因、实验结果、研究上下文或导出交接审计包。",
        "safety": "只读审计面；不执行实验、不修改外部 Runtime 状态、不读取外部 artifact URI。",
    },
    {
        "id": "benchmark_registry",
        "name": "评测合同与结果留痕",
        "primary_endpoint": "POST /api/v1/benchmarks",
        "next_endpoints": [
            "GET /api/v1/benchmarks/audit",
            "POST /api/v1/benchmark-runs",
            "GET /api/v1/benchmark-runs/compare",
            "PATCH /api/v1/benchmark-runs/{run_id}",
        ],
        "facts_from": "benchmarks, benchmark_runs",
        "when_to_use": "外部 Runtime 注册固定任务集、模型评测、Agent 记忆评测或 AI for Science 实验的 adapter 合同，并在执行后提交结果。",
        "safety": "平台不运行 benchmark，只保存 suite 合同、run 结果、artifact 引用和 provenance。",
    },
    {
        "id": "review_events",
        "name": "审查事件",
        "primary_endpoint": "POST /api/v1/reviews",
        "next_endpoints": ["GET /api/v1/reviews", "GET /api/v1/reviews/audit", "POST /api/v1/decisions"],
        "facts_from": "insights, research_experiments, benchmark_runs, artifacts, experiences",
        "when_to_use": "自动 critic、外部 Runtime 或必要的人类复核需要对证据、实验、评测或经验做审查、降级判断、质量门审计和风险标注。",
        "safety": "review 是审查事件，不代表平台自动接受结论；review audit 只读账本、不运行 critic；正式科研判断应写入 decision record。",
    },
    {
        "id": "evidence_records",
        "name": "证据记录",
        "primary_endpoint": "POST /api/v1/evidence-records",
        "next_endpoints": [
            "GET /api/v1/evidence-records",
            "GET /api/v1/evidence-records/summary",
            "POST /api/v1/reviews",
            "POST /api/v1/decisions",
        ],
        "facts_from": "sources, research_experiments, benchmark_runs, artifacts, reviews",
        "when_to_use": "外部 Runtime 需要把证据与 claim 绑定，并记录支持、反证、不确定、复现或复现失败及其质量限制。",
        "safety": "证据记录必须引用 evidence_refs；summary 只做确定性聚合、覆盖范围、质量缺口和复现计划建议，不执行实验、不自动接受结论。",
    },
    {
        "id": "decision_records",
        "name": "科研决策记录",
        "primary_endpoint": "POST /api/v1/decisions",
        "next_endpoints": ["GET /api/v1/decisions", "POST /api/v1/experiences/curation/preview"],
        "facts_from": "reviews, benchmark_runs, research_experiments, artifacts",
        "when_to_use": "将证据审查结果转成接受、拒绝、继续、阻塞、替代或归档等可审计科研判断。",
        "safety": "决策必须引用 evidence_refs；平台记录判断，不自动生成长期经验。",
    },
    {
        "id": "runtime_event_ledger",
        "name": "外部 Runtime 事件留痕",
        "primary_endpoint": "POST /api/v1/research/sessions/{session_id}/events",
        "next_endpoints": ["POST /api/v1/research/sessions/{session_id}/artifacts"],
        "facts_from": "research_events, research_artifacts",
        "when_to_use": "外部 Runtime 需要记录过程事件、外部输入摘要、阻塞原因或执行观察。",
        "safety": "平台只保存通用事件和 artifact 引用，不感知外部交互形态。",
    },
    {
        "id": "artifact_registry",
        "name": "成果引用索引",
        "primary_endpoint": "GET /api/v1/artifacts",
        "next_endpoints": [
            "GET /api/v1/artifacts/audit",
            "POST /api/v1/research/sessions/{session_id}/artifacts",
        ],
        "facts_from": "research_artifacts",
        "when_to_use": "跨 session 查询和审计研究结果、日志、数据集引用、benchmark 输出和报告索引。",
        "safety": "平台只保存并审计 artifact URI、hash、MIME、大小、存储位置和摘要，不保存或读取大文件和原文。",
    },
    {
        "id": "experience_curation",
        "name": "长期经验显式维护",
        "primary_endpoint": "POST /api/v1/experiences/query",
        "next_endpoints": [
            "POST /api/v1/experiences/curation/preview",
            "POST /api/v1/experiences/curation/apply",
        ],
        "facts_from": "experiences, experience_topics",
        "when_to_use": "开题前检索历史记忆，或收尾后由外部 Runtime 显式提交候选长期经验。",
        "safety": "平台不从 ledger 自动抽取经验。",
    },
]


def agent_guidance(
    *,
    when_to_use: str,
    facts_from: str,
    next_steps: list[str] | None = None,
    safety: str = "read/write through REST contract only",
    capability_group: str = "general",
    safety_level: str = "write",
    response_contract: str = "JSON response model documented in OpenAPI",
) -> dict[str, Any]:
    return {
        "x-agent-guidance": {
            "when_to_use": when_to_use,
            "facts_from": facts_from,
            "next_steps": next_steps or [],
            "safety": safety,
        },
        "x-capability-group": capability_group,
        "x-safety-level": safety_level,
        "x-agent-visible": True,
        "x-response-contract": response_contract,
    }


def install_agent_openapi(app: FastAPI) -> None:
    """Attach machine-readable Runtime capability metadata to OpenAPI."""

    original_openapi = app.openapi

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema
        schema = original_openapi()
        schema.setdefault("components", {}).setdefault("securitySchemes", {})["BearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "description": "Optional deployment token. When AUTORESEARCH_API_TOKEN is set, non-public API endpoints require Authorization: Bearer <token>.",
        }
        schema["x-agent-capabilities"] = AGENT_CAPABILITIES
        schema["x-agent-entrypoint"] = {
            "base_path": "/api/v1",
            "schema_path": "/api/v1/openapi.json",
            "openapi": "/api/v1/openapi.json",
            "docs": "/docs",
            "recommended_first_calls": [
                "GET /api/v1/agent/onboarding",
                "GET /api/v1/capabilities",
                "GET /api/v1/system/security",
                "GET /api/v1/system/readiness",
                "GET /api/v1/system/status",
                "POST /api/v1/experiences/query",
            ],
            "auth": {
                "scheme": "optional_bearer_token",
                "header": "Authorization: Bearer <token>",
                "discovery_endpoint": "GET /api/v1/system/security",
                "public_without_token": [
                    "GET /api/v1/openapi.json",
                    "GET /api/v1/agent/onboarding",
                    "GET /api/v1/capabilities",
                    "GET /api/v1/system/status",
                    "GET /api/v1/system/readiness",
                    "GET /api/v1/system/security",
                ],
            },
            "response_contract": "All public endpoints return {data, warnings}. Errors use HTTP status plus JSON detail.",
            "runtime_boundary": "External Runtime performs model calls, benchmark execution and agent loops.",
        }
        for path, methods in schema.get("paths", {}).items():
            for method, operation in methods.items():
                if method not in {"get", "post", "patch", "put", "delete"}:
                    continue
                operation.setdefault(
                    "x-agent-guidance",
                    {
                        "when_to_use": f"Use {method.upper()} {path} through the documented REST contract.",
                        "facts_from": "AutoResearch Platform REST state",
                        "next_steps": [],
                        "safety": "Follow endpoint-specific schema and preserve provenance.",
                    },
                )
                operation.setdefault("x-capability-group", (operation.get("tags") or ["general"])[0])
                operation.setdefault("x-safety-level", "read" if method == "get" else "write")
                operation.setdefault("x-agent-visible", True)
                operation.setdefault("x-response-contract", "JSON response model documented in OpenAPI")
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi

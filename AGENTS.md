# AGENTS.md

本项目工作语言使用中文，文档和编码不要使用 emoji。

## 核心边界

你是平台维护者，不是外部 Runtime。AutoResearch Platform 只提供 REST/OpenAPI 事实源、状态、账本、artifact 引用、经验维护和 React 工作台。

禁止在平台内实现或恢复:

- LLM provider router、fallback、限流、成本治理或 key 管理。
- 全双工语音模型、实时音频推理或音频原文存储。
- benchmark 执行器、模型训练、架构搜索或 agent loop。
- 直接读写外部 Runtime 的工作目录、数据库或临时脚本。
- 旧式 workflow DAG、自动经验抽取、embedding/RAG 原文表。

## API 约定

- 外部 Runtime 只能通过 `/api/v1/openapi.json` 发现和调用平台。
- 每个外部可见 endpoint 必须带 `x-agent-guidance`、`x-capability-group`、`x-safety-level`、`x-agent-visible` 和 `x-response-contract`。
- `blocked` 和 `degraded` 是合法状态，不能伪造结论。
- 长期经验只能通过 `POST /api/v1/experiences/curation/preview` 和 `POST /api/v1/experiences/curation/apply` 显式维护。
- 大 PDF、音频、视频、checkpoint、大 benchmark 输出不进 DB，只保存 artifact 引用。

## 目录

```text
backend/autoresearch_platform/  -> FastAPI 包
backend/migrations/             -> Alembic schema 合同
frontend/src/                   -> React 工作台
docs/architecture/              -> 架构和外部 Runtime 合同
.agents/skills/auto-research/   -> 外部 Agent 使用流程
```

## 验证

改动后至少运行:

```bash
make test
make openapi
```


# AutoResearch Platform

AutoResearch Platform 是面向外部科研 Runtime 的 REST/OpenAPI 事实源和 React 工作台。它用于保存资料输入、洞察、假设、研究计划、研究问题、预注册协议、研究队列、过程账本、artifact 引用、benchmark run、证据、审查事件、决策记录和长期经验。

## 它是什么

平台提供一套可审计的科研基础设施:

- REST/OpenAPI 合同，供外部 Runtime 自动发现和调用。
- 状态、上下文恢复包、研究就绪检查、研究轮次追踪包、证据质量缺口、artifact 元数据审计和显式经验维护。
- 中文 React 工作台，用于浏览、登记和审计研究过程。
- 科研方法论对象，支持从资料输入、上下文恢复、预注册协议到每轮研究留痕的闭环。
- 开源部署边界，默认 JSON store，可配置 PostgreSQL 持久化存储。

## 它不是什么

平台不执行科研工作本身。以下能力属于外部 Runtime 或部署环境:

- LLM provider router、fallback、限流、成本治理或 key 管理。
- benchmark 执行器、模型训练、架构搜索或 agent loop。
- 具体交互场景的一等模块。
- 外部 Runtime 工作目录、数据库或临时脚本的直接读写。
- 大 PDF、音频、视频、checkpoint、大 benchmark 输出或原文内容存储。

## 快速开始

```bash
make start local
make status
make test
make openapi
```

默认地址:

- API: `http://127.0.0.1:8010`
- 工作台: `http://127.0.0.1:5174`
- OpenAPI: `http://127.0.0.1:8010/api/v1/openapi.json`
- 安全状态: `http://127.0.0.1:8010/api/v1/system/security`
- 部署就绪: `http://127.0.0.1:8010/api/v1/system/readiness`

外部 Runtime 或开源部署方可以先跑只读接入校验:

```bash
python3 scripts/validate_agent_onboarding.py --base-url http://127.0.0.1:8010/api/v1
```

该脚本只读取 `GET /api/v1/agent/onboarding` 和 `GET /api/v1/openapi.json`，输出 JSON 报告，不执行实验、不读取 artifact URI、不访问外部 Runtime 工作目录，也不输出 token 值。

Docker 本地预览:

```bash
cp .env.example .env
docker compose up
```

## 外部 Runtime 合同

外部 Runtime 只能通过 `/api/v1/openapi.json` 发现平台能力。每个外部可见 endpoint 都必须带有:

- `x-agent-guidance`
- `x-capability-group`
- `x-safety-level`
- `x-agent-visible`
- `x-response-contract`

`blocked` 和 `degraded` 是合法状态。长期经验只能通过 `POST /api/v1/experiences/curation/preview` 和 `POST /api/v1/experiences/curation/apply` 显式维护。

外部 Runtime 应在正式调用前读取 `GET /api/v1/system/security`。默认本地开发不要求 token；生产部署可以设置 `AUTORESEARCH_API_TOKEN`，启用后非公开 API endpoint 必须带 `Authorization: Bearer <token>`。平台只把写操作和被拒绝请求的元数据写入 `logs` 审计账本，不保存请求正文、密钥或 artifact 原文。

## 科研方法论闭环

推荐流程:

```text
经验查询 -> 上下文恢复 -> 就绪检查 -> 资料输入 -> 洞察 -> 假设 -> 研究计划 -> 研究问题 -> 方法卡 -> 预注册协议 -> 研究队列 -> 研究账本 -> artifact/benchmark/evidence/review/decision -> 显式经验维护
```

`protocol` 是预注册记录，不是 workflow DAG。平台只登记研究设计和证据，不根据 protocol 执行实验。

## 工作台

React 工作台用于:

- 创建和浏览资料、洞察、队列、账本、benchmark、证据、决策和经验。
- 查看平台部署就绪状态，区分 JSON 开发模式、PostgreSQL schema 合同和持久化边界。
- 查看认证与审计状态，确认当前部署是否要求 Bearer token、哪些 endpoint 公开、写操作是否进入审计账本。
- 恢复研究上下文，查看已有事实、风险、证据状态和建议下一步。
- 在实验、审查、决策或经验维护前运行就绪检查，查看阻塞缺口、检查项和建议动作。
- 审计 artifact URI、hash、大小、存储位置和摘要是否足够支撑后续证据。
- 聚合科研主张的证据状态、覆盖范围、质量缺口和复现计划建议。
- 在写入决策前审计 review 是否包含审查来源、证据引用、说明、分数或风险。
- 登记研究轮次，查看追踪包，追踪方案、Worktree、Commit、实验、artifact、证据和决策引用。
- 导出只读研究审计包，用于 Agent 交接、复现实验和开源审查。
- 查看 API warnings、请求错误、阻塞和降级状态。
- 轻量登记 demo 数据，帮助外部 Runtime 验证 API 合同。

## 数据边界

artifact 只保存引用和元数据，例如 `uri`、`sha256`、`mime_type`、`size_bytes`、`storage` 和 `summary`。`GET /api/v1/artifacts/audit` 只审计这些元数据，不读取外部 URI。大文件、原文、二进制、媒体、checkpoint 和 benchmark dump 必须留在外部存储。

PostgreSQL schema 保留平台文本 ID，主键为 `id TEXT PRIMARY KEY`。这些 ID 是外部 Runtime、OpenAPI、工作台和研究轮次引用的一致性基础，不能替换成 UUID surrogate key。生产部署应先运行 Alembic 迁移，再设置 `AUTORESEARCH_STORE_BACKEND=postgres` 和 `AUTORESEARCH_DATABASE_URL`，最后用 `GET /api/v1/system/readiness` 验证状态为 `ready`。

`AUTORESEARCH_API_TOKEN` 是可选部署边界，不是 LLM provider key 管理。启用后只有公开入口、OpenAPI、能力目录、系统状态、部署就绪和安全状态可匿名读取；其他 API 调用需要 Bearer token。`GET /api/v1/system/audit-log` 可用于查看 metadata-only 审计记录，生产环境仍应由部署方配置 TLS、反向代理、日志保留和备份。

## 验证

改动后至少运行:

```bash
make test
make openapi
```

发布前建议运行:

```bash
make verify-release
```

## 路线图

- 补齐部署模板、数据库迁移运维手册和生产日志保留建议。
- 扩展 benchmark provenance、review 和经验治理的前端视图。
- 提供更多外部 Runtime cookbook 和示例数据。

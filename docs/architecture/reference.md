# AutoResearch Platform Architecture Reference

AutoResearch Platform 是外部科研 Runtime 的事实源。平台内只实现确定性维护接口和可浏览工作台。

## 能力层

| 层 | 职责 |
| --- | --- |
| Sources | 论文、URL、数据集、代码仓库、笔记、artifact 引用、模糊目标和外部 Runtime 输入 |
| Insights | 从 sources 提炼观点、机制解释、缺口和假设线索 |
| Research Methodology | 研究计划、研究问题、方法卡和预注册实验协议 |
| Research Context | 开题和恢复前的只读上下文包，聚合事实、证据、风险和建议下一步 |
| Research Rounds | 每轮方案、worktree/branch、commit、实验、artifact、证据和决策引用 |
| Research Intake | 外部 Runtime 或 Agent 提交、领取和启动研究任务 |
| Session Ledger | 研究事件、实验、artifact、收尾 retrospective |
| Artifact Registry | 外部成果引用索引、URI/hash/大小/存储/摘要元数据审计 |
| Benchmarks | benchmark suite 外部 adapter 合同、输入输出、指标、artifact 要求和 Runtime run 结果 |
| Evidence | 科研主张与支持、反证、不确定、复现或复现失败证据的绑定、聚合概览、覆盖范围、质量缺口和复现建议 |
| Reviews | 自动 critic、外部 Runtime 或必要人工复核的审查事件与 decision 前质量门 |
| Decisions | 接受、拒绝、继续、阻塞、替代或归档等证据绑定科研判断 |
| Runtime Event Ledger | 通用过程事件、外部输入摘要、阻塞原因和执行观察 |
| Experiences | 长期经验查询与显式 curation |
| Security And Audit | 可选 Bearer token 边界、公开入口说明、metadata-only API 审计 |

## 引用留痕

平台不内置科研实体关系推断层。研究过程追踪通过各类账本对象上的显式引用字段完成，包括 `source_refs`、`insight_refs`、`hypothesis_refs`、`implementation_refs`、`experiment_refs`、`artifact_refs`、`evidence_refs` 和 `decision_refs`。

研究轮次是每轮方案的主要留痕单位。外部 Runtime 可以在新方案中自行创建 worktree、提交 commit、运行实验并产出 artifact，但平台只保存这些动作的引用、状态、复盘和证据绑定，不生成关系图、不推断隐藏边。

## 状态

统一状态为 `planned`、`queued`、`claimed`、`running`、`completed`、`failed`、`rejected`、`superseded`、`blocked`、`degraded`、`archived`。

`blocked` 与 `degraded` 是合法结果，不应被强行改写成成功。

## 存储

本地默认使用 `data/autoresearch_store.json` 方便开发和演示。`backend/migrations/` 是 PostgreSQL durable deployment 的 schema 合同。Store 层不得运行 DDL。

`AUTORESEARCH_STORE_BACKEND=json` 是默认模式。`AUTORESEARCH_STORE_BACKEND=postgres` 只在部署显式配置 `AUTORESEARCH_DATABASE_URL` 后启动，并要求部署流程先运行 Alembic 迁移。PostgreSQL adapter 只读写平台表和 JSONB payload，不创建表、不运行迁移、不访问外部 Runtime 工作目录。

PostgreSQL schema 必须保留平台生成的文本 ID，主键合同为 `id TEXT PRIMARY KEY`。不得把 `source_`、`session_`、`round_`、`artifact_` 等稳定 ID 替换成 UUID surrogate key，否则会破坏 OpenAPI、工作台和外部 Runtime 的引用一致性。

`GET /api/v1/agent/onboarding` 是外部 Agent 和 Runtime 的公开只读接入自检包。它聚合安全状态、部署就绪、能力目录、`auto-research` Skill 加载顺序、建议首批调用、后续动作和 integrity 边界；它不返回 OpenAPI 全量正文、不访问外部 Runtime、不读取 artifact URI、不执行实验。外部 Runtime 应先读它，再按 `skill.load_order` 渐进加载 Skill references，并用 OpenAPI 校验 route/schema 漂移。开源部署方或带仓库副本的外部 Agent 可以运行 `python3 scripts/validate_agent_onboarding.py --base-url http://127.0.0.1:8010/api/v1` 做只读 smoke 校验；该脚本只读取 onboarding 和 OpenAPI，不写入平台。

`GET /api/v1/system/readiness` 是部署前的只读就绪检查。它读取 store health 与 Alembic schema 合同，返回 `ready`、`degraded` 或 `blocked`，用于明确区分开发演示、数据库结构缺口和生产可接入状态。JSON store 会报告 `degraded`；PostgreSQL 连通且 schema 覆盖全部 collection 时可以报告 `ready`。

`GET /api/v1/system/security` 是部署安全状态入口。默认本地开发不要求 token；设置 `AUTORESEARCH_API_TOKEN` 后，公开入口、OpenAPI、Agent 接入自检包、能力目录、系统状态、部署就绪和安全状态以外的 API endpoint 必须带 Bearer token。`GET /api/v1/system/audit-log` 返回写操作和被拒绝请求的 metadata-only 记录，用于追踪 actor、路径、状态码和认证结果；平台不得保存请求正文、Bearer token、外部 Runtime 原文或大 artifact 内容。

平台不得为举例场景创建一等模块。任意具体交互形态都属于外部 Runtime；平台只保存通用 sources、session events 和 artifact references。

Artifact 记录必须是外部对象引用。平台可以保存 `uri`、`sha256`、`mime_type`、`size_bytes`、`storage`、`summary` 和小型 metadata payload，但不得保存原文、二进制、媒体、checkpoint 或大输出。Artifact audit 只能检查这些元数据是否齐全，不访问 URI 或外部存储。

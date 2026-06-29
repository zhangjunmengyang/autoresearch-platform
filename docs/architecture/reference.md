# AutoResearch Platform Architecture Reference

AutoResearch Platform 是外部科研 Runtime 的事实源。平台内只实现确定性维护接口和可浏览工作台。

## 方法论闭环

AutoResearch Platform 的生产主线不是对象管理系统，而是外部 Runtime 的研究闭环事实源。React 工作台是人类观察面，只展示 deployments、research runs、outputs、质量门和阻塞状态；闭环推进由外部 Runtime 通过 REST/OpenAPI 完成。

```text
Idea Pool -> Hypothesis -> Plan -> Experiment -> Result -> Review -> Decision -> Lesson -> Next Hypothesis
```

FARS 风格的人类看板使用更粗的阶段名展示同一条链路:

```text
Ideation -> Planning -> Experimentation -> Writing -> Review -> Decision
```

| 层 | 职责 |
| --- | --- |
| Idea Pool | 论文、repo、数据集、benchmark gap、研究员想法、历史失败和外部观察 |
| Hypothesis | 本轮要验证的研究假设，必须能追溯到 idea 来源 |
| Plan | 最小研究计划，记录唯一变化、验证方式、接受/拒绝标准和结果要求；不是 workflow DAG |
| Experiment | 外部 Runtime 的一次执行记录；平台不执行实验、不训练模型、不调度资源 |
| Result | 分数、日志、图表、论文草稿、badcase 文件等外部 artifact 引用和轻量摘要 |
| Review | 对 result 的解释、复盘、审查或 artifact-aware review |
| Decision | `keep`、`discard`、`continue`、`retry`、`blocked`、`archived` 等迭代判断 |
| Lesson | 显式沉淀的可复用经验，用来指导下一轮 hypothesis 或 plan |

当前 canonical API 优先使用 `GET /api/v1/method-loop`、`POST /api/v1/ideas`、`POST /api/v1/hypotheses`、`POST /api/v1/plans`、`POST /api/v1/results`、`POST /api/v1/reviews`、`POST /api/v1/decisions` 和 `POST /api/v1/experiences/curation/preview|apply`。旧的 sources、protocols、sessions、rounds、artifacts、evidence records、reviews、decisions 和 experiences 仍是底层存储与高级审计映射，不应作为平级主导航暴露。

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

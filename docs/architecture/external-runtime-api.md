# External Runtime API

外部 Runtime 的机器合同入口是 `/api/v1/openapi.json`。首次接入时先读取 `GET /api/v1/agent/onboarding`，它聚合认证、部署就绪、能力目录、Skill 加载顺序和建议首批调用；OpenAPI 仍是 route/schema 的最终校验源。每个 endpoint 都带有:

- `x-agent-guidance`
- `x-capability-group`
- `x-safety-level`
- `x-agent-visible`
- `x-response-contract`

仓库提供一个只读 smoke 校验器，适合开源部署方或带有仓库副本的外部 Agent 在正式研究前运行:

```bash
python3 scripts/validate_agent_onboarding.py --base-url http://127.0.0.1:8010/api/v1
```

如部署启用了 `AUTORESEARCH_API_TOKEN`，把 token 放在同名环境变量中，脚本只会报告 `token_present`，不会打印 token 值。脚本只读取 `GET /api/v1/agent/onboarding` 和 `GET /api/v1/openapi.json`，校验 onboarding schema、只读 integrity、Skill 加载顺序、建议首批调用、OpenAPI entrypoint 和每个 operation 的 Agent 元数据。返回 `status=pass` 时退出码为 0；返回 `status=fail` 时退出码为 2。`onboarding_state=degraded` 仍可能通过 smoke，它表示部署可用于本地或降级研究，但外部 Runtime 应把限制写入 session。

## 默认流程

1. `GET /api/v1/agent/onboarding` 读取接入自检包，确认认证、部署就绪、能力组、Skill 加载顺序和建议首批调用。
2. `GET /api/v1/system/security` 检查当前部署是否要求 Bearer token；需要 token 时，后续非公开 endpoint 必须带 `Authorization: Bearer <token>`。
3. `GET /api/v1/system/readiness` 检查平台部署、存储和 schema 是否允许正式研究。
4. `POST /api/v1/experiences/query` 读取历史经验。
5. `GET /api/v1/research/context?query=...&claim=...` 恢复已有事实、风险、证据状态和建议下一步。
6. `GET /api/v1/research/rounds/{round_id}` 在继续已有轮次前恢复追踪包。
7. `GET /api/v1/research/readiness?query=...&claim=...&round_id=...&stage=...` 在实验、审查、决策或经验维护前做只读就绪检查。
8. `POST /api/v1/research/rounds` 登记本轮方案、worktree/branch 引用和状态。
9. `POST /api/v1/sources` 写入论文、资料、artifact 引用、外部 Runtime 输入或模糊目标输入。
10. `POST /api/v1/insights` 和 `POST /api/v1/hypotheses` 写入 insight 与可验证假设。
11. `POST /api/v1/research/programs`、`questions`、`method-cards` 和 `protocols` 登记科研设计和预注册协议。
12. `GET /api/v1/research/design/audit` 审计问题、假设和协议是否可回答、可证伪、可审计。
13. `POST /api/v1/research/intake` 创建待研究任务。
14. `POST /api/v1/research/intake/{item_id}/claim` 领取任务。
15. `POST /api/v1/research/intake/{item_id}/start-session` 启动 session。
16. `POST /api/v1/research/sessions/{session_id}/events` 记录过程事件。
17. `POST /api/v1/research/sessions/{session_id}/experiments` 预注册实验。
18. `GET /api/v1/benchmarks/audit` 在运行评测前审计 suite adapter、输入、输出、指标和 artifact 要求。
19. `POST /api/v1/benchmark-runs` 或 artifact endpoint 写入执行结果。
20. `GET /api/v1/benchmark-runs/compare?benchmark_id=...&metric=...` 对多个 run 做只读分数、状态、最佳 run 和证据准备缺口对比。
21. `GET /api/v1/artifacts/audit?session_id=...` 审计 artifact 元数据是否足够作为证据。
22. `PATCH /api/v1/research/rounds/{round_id}` 回填 commit、experiment、artifact、evidence 或 decision 引用。
23. `GET /api/v1/research/rounds/{round_id}` 校验追踪包、warnings 和 `unresolved_refs`。
24. `POST /api/v1/evidence-records` 写入科研主张与证据的支持、反证、不确定或复现关系。
25. `GET /api/v1/evidence-records/summary?claim=...` 聚合科研主张的支持、反证、不确定、复现状态、覆盖范围、质量缺口和复现计划建议。
26. `POST /api/v1/reviews` 写入自动 critic、外部 Runtime 或必要人工复核的审查结果。
27. `GET /api/v1/reviews/audit?q=...` 审计 review 是否足够支撑 decision。
28. `POST /api/v1/decisions` 写入基于证据的科研决策。
29. `GET /api/v1/research/audit/export?query=...&claim=...&session_id=...&round_id=...` 导出只读审计包，用于交接、复现或开源审查。
30. `POST /api/v1/research/sessions/{session_id}/close` 收尾。
31. `POST /api/v1/experiences/curation/preview` 和 `apply` 显式沉淀长期经验。

## Security And Audit Contract

`GET /api/v1/agent/onboarding` 是公开只读接入包，返回 `schema`、`state`、`openapi`、`docs`、`skill`、`security`、`readiness`、`capability_groups`、`recommended_first_calls`、`recommended_next_actions`、`integrity` 和 `safety`。它不返回 OpenAPI 全量正文、不访问外部 Runtime、不读取 artifact URI、不执行实验；外部 Runtime 应先读它，再按 `skill.load_order` 渐进加载 `auto-research` references，并用 OpenAPI 校验 route/schema 漂移。

`GET /api/v1/system/security` 是公开只读入口，返回认证是否启用、公开 endpoint、保护范围、审计策略和安全说明。外部 Runtime 不应猜测部署模式，应以该 endpoint 和 OpenAPI `x-agent-entrypoint.auth` 为准。

启用 `AUTORESEARCH_API_TOKEN` 时，外部 Runtime 对非公开 endpoint 使用 `Authorization: Bearer <token>`。token 由部署环境注入，不能写入 source、event、artifact metadata、experience、review、decision 或审计说明。

平台会把写操作和被拒绝请求写入 `logs` collection。审计记录只包含请求方法、路径、状态码、actor、认证结果、query key、content type 和 user agent 等元数据；不保存请求正文、Bearer token、LLM provider key、大型 artifact、外部 Runtime 原文或 checkpoint。`GET /api/v1/system/audit-log` 可用于只读审计，生产保留策略仍由部署环境负责。

## 场景边界

平台不得为举例场景创建一等模块。任意具体交互形态都由外部 Runtime 处理；平台只接收通用 source、session event 和 artifact reference。

## List Query Contract

List endpoint 在标准 `{data,warnings}` envelope 内返回 `{items,total,limit,offset,sort}`。外部 Runtime 应使用 `status`、`q`、`limit`、`offset` 和 `sort` 查询参数恢复任务、筛选状态和分页审计，不应读取或扫描本地 store 文件。

核心 list endpoints:

- `GET /api/v1/sources`
- `GET /api/v1/insights`
- `GET /api/v1/hypotheses`
- `GET /api/v1/research/programs`
- `GET /api/v1/research/questions`
- `GET /api/v1/research/method-cards`
- `GET /api/v1/research/protocols`
- `GET /api/v1/research/design/audit`
- `GET /api/v1/research/intake`
- `GET /api/v1/research/context`
- `GET /api/v1/research/readiness`
- `GET /api/v1/research/rounds`
- `GET /api/v1/research/rounds/{round_id}`
- `GET /api/v1/research/sessions`
- `GET /api/v1/research/events`
- `GET /api/v1/research/experiments`
- `GET /api/v1/artifacts`
- `GET /api/v1/artifacts/audit`
- `GET /api/v1/benchmarks`
- `GET /api/v1/benchmarks/audit`
- `GET /api/v1/benchmark-runs`
- `GET /api/v1/evidence-records`
- `GET /api/v1/evidence-records/summary`
- `GET /api/v1/reviews`
- `GET /api/v1/reviews/audit`
- `GET /api/v1/research/audit/export`
- `GET /api/v1/decisions`
- `GET /api/v1/experiences`

## Artifact Reference Contract

`POST /api/v1/research/sessions/{session_id}/artifacts` 只登记外部 artifact 引用。外部 Runtime 应提交 `uri`、`sha256`、`mime_type`、`size_bytes`、`storage`、`summary` 和小型 metadata payload。平台会拒绝原文、二进制、媒体、checkpoint、大型 benchmark 输出和其他内联内容；这些内容必须留在外部存储。

`GET /api/v1/artifacts` 是跨 session 的全局成果索引，支持 `q`、`limit`、`offset` 和 `sort`。外部 Runtime 应通过它恢复已有结果、查找可复用数据集引用和审计 benchmark 输出，不应扫描本地 store 文件或外部 Runtime 工作目录。

`GET /api/v1/artifacts/audit?session_id=...&q=...` 是只读元数据审计。它只检查平台内 artifact 记录是否包含 URI、hash、size、storage 和 summary，并返回 `state`、`issue_counts`、`artifact_ids_with_issues`、逐条 `items` 和 `recommended_next_actions`。它不会访问 URI、不会读取外部存储，也不会下载大文件；返回 `blocked` 时，外部 Runtime 应重新登记更完整的 artifact 引用，再把 artifact 写入 evidence、review 或 decision。

Runtime event 使用 `event_type=runtime_event` 写入通用过程账本。事件 payload 应使用 `summary`、`artifact_refs`、`source_refs`、`runtime`、`provenance` 等通用字段，不应暴露或要求平台理解外部交互形态。

## Research Audit Contract

`GET /api/v1/research/events` 和 `GET /api/v1/research/experiments` 是跨 session 的只读审计入口。外部 Runtime 应用它们恢复失败尝试、阻塞原因、实验状态和可复现实验记录。实验列表支持 `status` 过滤；事件列表使用 `q`、`limit`、`offset` 和 `sort` 查询，不要求平台理解外部交互形态。

`GET /api/v1/research/context?query=...&claim=...` 是开题和恢复前的只读上下文包。它按关键词聚合 sources、insights、hypotheses、methodology、intake、sessions、events、experiments、artifacts、benchmark runs、evidence、reviews、decisions 和 experiences，返回 `counts`、`sections`、`evidence_summary`、`risk_flags` 和 `recommended_next_actions`。外部 Runtime 应把它当作缺口和冗余检查入口，而不是执行计划；平台不会根据这些建议自动调用后续 endpoint。

`GET /api/v1/research/readiness?query=...&claim=...&round_id=...&stage=...` 是只读 preflight。它复用上下文恢复、轮次追踪包和证据概览，返回 `state`、`checks`、`blocking_gaps`、`warning_gaps`、`context`、`round_trace`、warnings 和 `recommended_next_actions`。`stage` 可用于区分 `before_experiment`、`before_review`、`before_decision` 和 `before_curation`。返回 `blocked` 时，外部 Runtime 应先补齐引用、实验、证据或决策，不应继续执行后续阶段。

`POST /api/v1/research/rounds`、`GET /api/v1/research/rounds`、`GET /api/v1/research/rounds/{round_id}` 和 `PATCH /api/v1/research/rounds/{round_id}` 是每轮研究留痕入口。外部 Runtime 应在新方案开始时登记 proposal、session、worktree path、branch 和 base ref；在实现、提交、实验、artifact、证据或决策产生后回填 `implementation_refs`、`experiment_refs`、`artifact_refs`、`evidence_refs` 和 `decision_refs`。轮次追踪包会解析这些显式引用，返回 resolved records、`unresolved_refs`、warnings 和 `recommended_next_actions`。平台只保存引用和状态，不创建 worktree、不执行 git、不读取外部工作目录。`completed` 的 round 必须至少包含一种追踪引用，否则平台返回 `422`；存在 `unresolved_refs` 时，外部 Runtime 应修正引用或保持 `blocked`/`degraded`，不能把该轮当作完整证据。

`GET /api/v1/research/audit/export?query=...&claim=...&session_id=...&round_id=...` 是只读研究审计包。它组合 context、session ledger、round trace、artifact audit、review audit、reproducibility、integrity 和 recommended actions，用于 Agent 交接、复现实验和开源审查。它不读取外部 artifact URI、不读取外部 Runtime 工作目录、不执行实验、不推断隐藏关系。

`reproducibility` 子包返回 `schema`、`state`、`checklist`、`external_artifacts` 和 `handoff_steps`。`checklist` 会显式标出 session ledger、round trace、artifact metadata、review gate 和 evidence summary 的 pass/warn/fail 状态；`external_artifacts` 只列出 URI、hash、大小、存储和摘要等引用元数据，并标记 `requires_external_verification`。外部 Runtime 应在自己的环境中验证这些 URI 和 hash，不能要求平台读取对象。

## Research Methodology Contract

科研方法论对象用于登记设计，不用于执行。外部 Runtime 可以按以下顺序登记:

```text
method template -> research program -> research question -> method card -> protocol -> intake item
```

`GET /api/v1/research/method-templates` 是只读方法模板目录，提供文献综合、复现、消融、评测对比和失败分析等通用自动化科研设计脚手架。每个模板返回 `design_questions`、`required_records`、`protocol_defaults`、`artifact_requirements`、`evidence_expectations`、`review_gates` 和 `next_endpoints`。模板不进入 DB，不执行实验，不创建 workflow DAG；外部 Runtime 必须显式登记 method card、protocol、artifact、evidence 和 review。

`protocol` 是预注册对象，记录研究问题、方法卡、唯一变化、对照、接受标准、拒绝标准和 artifact 要求。平台不得把 protocol 当作 workflow DAG，也不得根据 protocol 执行实验。

`GET /api/v1/research/design/audit?q=...` 是实验前的只读设计质量门。它检查研究问题是否有 `success_criteria`，假设是否有 `expected_effect`、接受标准和拒绝标准，协议是否有 controls、接受/拒绝标准、artifact requirements、方法卡和假设关联。返回 `blocked` 时，外部 Runtime 应先修复设计，不应继续 intake、实验或 benchmark。

## Benchmark, Evidence And Review Contract

平台只登记 benchmark suite、run 状态、分数、artifact 引用和 provenance，不执行 benchmark。Benchmark suite 应包含 `external_runner`、`input_schema`、`output_schema`、`metric_schema` 和 `artifact_requirements`，用于描述外部 Runtime 的 adapter 合同、所需输入、结果输出、分数字段和完成后必须登记的 artifact 类型。

`GET /api/v1/benchmarks/audit?q=...` 是运行评测前的只读质量门。它返回 `state`、`issue_counts`、`benchmark_ids_with_issues`、逐条 suite `items`、合同摘要和 `recommended_next_actions`。缺少外部 runner、输入、输出、指标或 artifact 要求时返回 `blocked`；外部 Runtime 应先补齐 suite 合同，再执行 benchmark。该 endpoint 不读取数据集、不调用模型、不执行评测。

`completed` 的 benchmark run 如果包含 `scores`，必须包含 `artifact_refs` 或 `provenance.runner`，否则平台返回 `422`。

`GET /api/v1/benchmark-runs/compare?benchmark_id=...&metric=...` 是提交多个 run 后的只读对比入口。它返回 `state`、`status_counts`、`best_run`、`score_range`、`ranked_runs`、`issue_counts`、`run_ids_with_issues` 和 `recommended_next_actions`，用于选择最佳 run、发现缺 artifact/provenance 的证据准备缺口，或决定是否补写 evidence record。该 endpoint 不执行 benchmark、不读取 artifact URI、不调用模型。

证据记录通过 `POST /api/v1/evidence-records` 写入，并通过 `GET /api/v1/evidence-records` 分页审计。每条 evidence record 必须包含 `evidence_refs`，用于把科研主张与支持、反证、不确定、复现或复现失败证据绑定。平台只保存证据判断和引用，不替外部 Runtime 接受结论。

`GET /api/v1/evidence-records/summary?claim=...` 对完整科研主张做大小写无关的精确聚合，返回 `total`、`stances`、`confidence`、`evidence_ids`、`limitations`、`coverage`、`quality_gaps`、`replication_plan`、`state` 和 `recommended_next_action`。这个 endpoint 只读且确定性，不生成结论；外部 Runtime 应根据返回状态、质量缺口和复现计划继续收证、登记复现、排查冲突、进入审查或写入决策。

审查结果通过 `POST /api/v1/reviews` 写入，并通过 `GET /api/v1/reviews` 分页审计。review 的 `verdict` 会同步为标准 `status`，因此外部 Runtime 可以用 `status`、`q`、`limit`、`offset` 和 `sort` 查询审查账本。

`GET /api/v1/reviews/audit?q=...` 是 decision 前的只读质量门。它返回 `state`、`issue_counts`、`review_ids_with_issues`、逐条 `items` 和 `recommended_next_actions`，检查 review 是否包含 subject、reviewer provenance、comments、evidence_refs、score 或 concerns。它不会调用 critic、不会运行模型、不会自动接受结论；返回 `blocked` 时，外部 Runtime 应先重写更完整的 review，再写 decision。

## Decision Record Contract

科研决策通过 `POST /api/v1/decisions` 显式写入，并通过 `GET /api/v1/decisions` 分页审计。决策必须包含 `evidence_refs`，否则平台返回 `422`。

决策记录用于表达对假设、实验、评测、审查、artifact 或长期经验的接受、拒绝、继续、阻塞、替代或归档。平台只保存判断、证据引用、标准和下一步，不自动生成长期经验，也不替外部 Runtime 执行后续动作。

## Experience Curation Lifecycle

长期经验只通过 `preview` 和 `apply` 显式维护。`apply` 必须包含可解析的 `source_refs`，否则平台返回 `422`。`preview` 返回 `source_trace`、`governance_gaps`、`recommended_next_actions` 和只读 `safety` 标记；任何 `unresolved_source_refs` 阻塞缺口都必须先修复，不能把不可解析引用写成长期经验。

`action` 语义:

- `create`: 创建 `candidate` 经验。
- `update`: 通过 `experience.id` 更新已有经验。
- `reject`: 创建或更新 `rejected` 经验。
- `supersede`: 将 `experience.supersedes` 指向的旧经验标记为 `superseded`，再创建继任 `candidate` 经验。
- `topic_summary`: 更新经验专题摘要。

外部 Runtime 不应把 session 字段机械复制为长期经验；应把 ledger、artifact、benchmark、evidence、review 和 decision 综合后再提交可读、可审计的 curation payload。平台允许 session、artifact 和 benchmark run 作为来源，但长期复用前应优先绑定 evidence record、review 或 decision。人工输入只作为目标、约束或审批 provenance，不是默认执行路径。

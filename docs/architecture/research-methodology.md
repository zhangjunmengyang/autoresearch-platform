# Research Methodology

每个正式研究都遵循:

1. 先查历史经验和失败路线。
2. 读取研究上下文恢复包，确认已有事实、风险、证据状态和建议下一步。
3. 写清外部约束和本轮信息增量；人工输入只作为模糊目标或审批 provenance。
4. 新方案登记 research round；如果涉及代码或实验配置，外部 Runtime 在自己的环境中创建 worktree/branch，并只把引用写回平台。
5. 继续已有方案时读取 round trace pack，确认已解析引用、warnings 和 `unresolved_refs`。
6. 新建方法卡或协议前读取 method templates，选择文献综合、复现、消融、评测对比或失败分析等通用设计模板。
7. 在 intake 或实验前运行 research design audit，确认问题可回答、假设可证伪、协议包含对照和 artifact 要求。
8. 在实验、审查、决策和经验维护前运行 readiness check；`blocked` 代表必须先修复缺口。
9. 将论文、资料、目标输入、artifact 引用或外部 Runtime 输入作为 source 留痕。
10. 从 source 产生 insight，再转成 hypothesis。
11. 每个实验只验证一个机制，先写 expected effect、acceptance criteria 和 rejection criteria。
12. benchmark 和实验由外部 Runtime 执行；运行 benchmark 前先审计 suite 合同，平台只接收 adapter 合同、结果和 artifact 引用。
13. benchmark/artifact 后先写 evidence record，再查询 evidence summary，之后进入 review、review audit、decision 和 curation。
14. 收尾必须记录 failed attempts、platform gaps、validated lessons 和 next agent one-liner。
15. 长期经验必须能让没参与本轮研究的 Agent 直接接手。

## 方法论对象

正式研究的设计链路是:

```text
经验查询 -> 上下文恢复 -> 研究轮次 -> 追踪包校验 -> 就绪检查 -> 研究计划 -> 研究问题 -> 方法卡 -> 实验协议 -> 研究队列 -> 研究账本 -> 实验结果/artifact -> 证据记录 -> 证据概览 -> 审查 -> 决策 -> 经验维护
```

研究计划记录长期目标、领域和硬约束。研究问题记录可回答问题和成功标准。`GET /api/v1/research/method-templates` 返回只读方法模板目录，覆盖文献综合、复现实验、消融实验、评测对比和失败分析。模板用于帮助外部 Runtime 准备方法卡、协议、artifact 要求、证据期望和审查门，不是实验设计生成器，也不会创建工作流或执行 benchmark。方法卡记录某类方法的适用场景、失败模式和所需 artifact。实验协议记录问题、方法、唯一变化、对照、接受标准和拒绝标准。

`protocol` 是预注册对象，不是可执行 DAG。平台不得根据协议执行实验、调模型、运行 benchmark 或编排 agent loop；外部 Runtime 只能读取协议并在自己的执行环境中运行实验，再把结果和 artifact 引用写回平台。

`research round` 是每轮方案留痕对象，不是 git 执行器。平台只保存 proposal、worktree/branch、commit、experiment、artifact、evidence 和 decision 引用；创建 worktree、提交代码和运行实验均由外部 Runtime 自行完成。`GET /api/v1/research/rounds/{round_id}` 返回该轮追踪包，用于恢复已解析记录、未解析引用和下一步修复动作；它不推断隐藏关系，也不执行任何外部动作。

`research design audit` 是 intake 和实验前的只读质量门，不是实验设计生成器。它检查研究问题是否可回答、假设是否有预期效应和接受/拒绝标准、协议是否有对照、唯一变化、artifact 要求、方法卡和假设关联。返回 `blocked` 时，外部 Runtime 应先补齐设计记录，不应继续执行实验。

`readiness check` 是只读阶段门，不是执行器。它聚合上下文、round trace、实验预注册、证据概览和决策状态，返回 `ready`、`degraded` 或 `blocked`。外部 Runtime 可以用它决定是否继续实验、进入审查、写决策或沉淀经验；平台不会根据检查结果自动执行动作。

`evidence summary` 是主张级证据审计，不是结论生成器。它返回 stance/confidence 计数、覆盖范围、质量缺口和复现计划建议；外部 Runtime 应把 `quality_gaps` 作为下一轮研究输入，优先补独立复现、跨 session 证据、对象绑定和限制说明。

## 长期经验维护

长期经验只能通过显式 curation 维护，不能从 session ledger 自动抽取。外部 Runtime 必须先调用 `POST /api/v1/experiences/curation/preview`，审阅 `warnings`、`source_trace`、`governance_gaps` 和 `recommended_next_actions` 后再调用 `POST /api/v1/experiences/curation/apply`；存在阻塞型治理缺口时不能写入长期经验。

支持的维护动作:

- `create`: 创建候选经验，状态为 `candidate`。
- `update`: 使用 `experience.id` 更新已有经验。
- `reject`: 创建或更新一条被拒绝经验，状态为 `rejected`。
- `supersede`: 将旧经验标为 `superseded`，并创建一条继任候选经验。
- `topic_summary`: 显式维护经验专题摘要。

每次经验维护都必须带可解析的 `source_refs`。证据可以来自研究账本、artifact、benchmark run、evidence record、review、decision 或其他平台记录；缺少证据引用或引用无法解析的 apply 请求必须被拒绝。session、artifact 和 benchmark run 可以作为来源，但长期经验应尽量补齐 evidence record、review 或 decision。

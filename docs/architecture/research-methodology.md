# Research Methodology

正式研究遵循一个可迭代闭环:

```text
Idea Pool -> Hypothesis -> Plan -> Experiment -> Result -> Review -> Decision -> Lesson -> Next Hypothesis
```

1. **Idea Pool**: 先查论文、repo、数据集、benchmark gap、研究员想法、历史失败、外部观察和长期经验。
2. **Hypothesis**: 把 idea 收敛成一个可验证假设，写清 expected effect、接受标准和拒绝标准。
3. **Plan**: 写最小实验计划，只验证一个机制，声明唯一变化、对照、结果要求和阻塞条件。
4. **Experiment**: 外部 Runtime 在自己的环境中运行实验、benchmark、复现、仿真、文献验证或代码实验；平台只保存执行引用和状态。
5. **Result**: 平台接收分数、日志、图表、badcase、commit、报告或论文草稿等外部 artifact 引用和轻量摘要。
6. **Review**: 对 result 做解释、复盘、artifact-aware review、复现检查或质量缺口审计；`blocked` 和 `degraded` 是合法结果。
7. **Decision**: 写入 `keep`、`discard`、`continue`、`retry`、`blocked` 或 `archived` 等判断，不伪造成完成。
8. **Lesson**: 只有明确来源和证据的经验才能通过 preview/apply 显式沉淀，并用于下一轮 hypothesis 或 plan。

## 方法论对象

当前 API 对这个闭环的实现映射是:

```text
experiences/context/ideas -> hypotheses -> plans -> sessions/rounds/experiments -> results/benchmark runs -> evidence/reviews -> decisions -> experiences
```

研究计划、研究问题和方法卡是高级治理对象，不是主路径入口。`GET /api/v1/research/method-templates` 返回只读方法模板目录，覆盖文献综合、复现实验、消融实验、评测对比和失败分析。模板用于帮助外部 Runtime 准备 plan、artifact 要求、review gate 和 lesson 来源，不是实验设计生成器，也不会创建工作流或执行 benchmark。实验协议记录问题、方法、唯一变化、对照、接受标准和拒绝标准。

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

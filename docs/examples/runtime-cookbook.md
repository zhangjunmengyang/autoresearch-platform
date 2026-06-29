# 外部 Runtime Cookbook

这个示例描述外部 Runtime 如何把一次自动化研究写入 AutoResearch Platform。平台只保存事实、状态和引用，不执行实验。

## 基本原则

- 如果外部 Runtime 持有仓库副本，正式研究前先运行 `python3 scripts/validate_agent_onboarding.py --base-url http://127.0.0.1:8010/api/v1`，确认接入包和 OpenAPI 元数据没有漂移。
- 启动时先读取 `/api/v1/agent/onboarding`，拿到认证、就绪、能力组、Skill 加载顺序和建议首批调用。
- 使用 `/api/v1/openapi.json` 校验 route/schema 漂移，必要时再读 `/api/v1/capabilities`。
- 启动时读取 `/api/v1/system/security`，确认是否需要 Bearer token；token 只能来自部署环境，不能写入平台记录。
- 正式研究前先读取 `/api/v1/system/readiness`。生产运行应为 `ready`；本地 JSON 开发模式返回 `degraded` 时，应把这个限制写入 session。
- 开题前先查长期经验。
- 正式写入前先读 `/api/v1/research/context?query=...&claim=...`，检查已有事实、风险、证据状态和建议下一步。
- 新方案开始时先登记 research round；如果需要改代码或实验配置，外部 Runtime 在自己的环境中创建 worktree/branch，然后只把引用写回平台。
- 继续已有方案时先读 `/api/v1/research/rounds/{round_id}`，确认追踪包、warnings 和 `unresolved_refs`。
- 进入实验、审查、决策或经验维护前先读 `/api/v1/research/readiness`，如果返回 `blocked`，先修复缺口。
- 执行前读取 `/api/v1/research/method-templates`，再登记假设、方法对象和预注册协议，并读取 `/api/v1/research/design/audit` 修复设计缺口。
- 运行 benchmark 前先读 `/api/v1/benchmarks/audit`，确认 suite 已声明外部适配器、输入、输出、指标和成果要求。
- 提交多个 benchmark run 后先读 `/api/v1/benchmark-runs/compare`，用只读对比选择最佳 run、发现缺 artifact/provenance 的证据准备缺口。
- 执行过程写 session event、experiment、artifact reference。
- 结果不完整时使用 `blocked` 或 `degraded`。
- benchmark/artifact 之后先跑 artifact audit，再写 evidence record，查询 evidence summary，写 review，运行 review audit，然后进入 decision。
- 交接、复现或开源审查前导出只读审计包，不读取外部 URI 或 Runtime 工作目录。
- 长期经验必须先 `preview`，再由外部 Runtime `apply`；人工输入只作为目标、约束或审批 provenance。

## 接入 Smoke

本仓库的接入校验器适合部署后或 Agent 接手前运行:

```bash
python3 scripts/validate_agent_onboarding.py --base-url http://127.0.0.1:8010/api/v1
```

脚本输出机器可读 JSON，检查 `agent/onboarding` 与 OpenAPI 的一致性、只读边界、Skill 加载顺序、建议首批调用和所有 operation 的 Agent 元数据。它不会写平台数据，不会执行 benchmark，不会读取 artifact URI，也不会访问外部 Runtime 工作目录。`status=pass` 表示接入合同可用；如果 `onboarding_state=degraded`，仍需在研究 session 中记录当前部署限制。

## 最小闭环

1. 接入自检: `GET /api/v1/agent/onboarding`
2. 查平台部署就绪: `GET /api/v1/system/readiness`
3. 查安全状态: `GET /api/v1/system/security`
4. 查能力: `GET /api/v1/capabilities`
5. 查经验: `POST /api/v1/experiences/query`
6. 恢复上下文: `GET /api/v1/research/context?query=...&claim=...`
7. 恢复已有轮次: `GET /api/v1/research/rounds/{round_id}`
8. 就绪检查: `GET /api/v1/research/readiness?query=...&claim=...&round_id=...&stage=before_experiment`
9. 登记研究轮次: `POST /api/v1/research/rounds`
10. 写资料: `POST /api/v1/sources`
11. 写洞察: `POST /api/v1/insights`
12. 写假设: `POST /api/v1/hypotheses`
13. 读取方法模板: `GET /api/v1/research/method-templates`
14. 写研究计划、问题、方法卡和协议
15. 审计研究设计: `GET /api/v1/research/design/audit`
16. 创建 intake 并启动 session
17. 记录事件、实验和 artifact 引用
18. 审计 benchmark 合同: `GET /api/v1/benchmarks/audit`
19. 提交 benchmark run
20. 对比 benchmark runs: `GET /api/v1/benchmark-runs/compare?benchmark_id=...&metric=...`
21. 审计 artifact 元数据: `GET /api/v1/artifacts/audit?session_id=...`
22. 回填轮次引用: `PATCH /api/v1/research/rounds/{round_id}`
23. 校验轮次追踪包: `GET /api/v1/research/rounds/{round_id}`
24. 决策前就绪检查: `GET /api/v1/research/readiness?stage=before_decision`
25. 写入 evidence record
26. 查询 evidence summary，判断是否需要继续收证、复现、补覆盖范围或排查冲突
27. 提交自动审查
28. 运行 review audit
29. 写入 evidence-backed decision
30. 导出只读审计包: `GET /api/v1/research/audit/export?query=...&claim=...&session_id=...&round_id=...`
31. 关闭 session
32. 预检并写入长期经验

## 认证与审计

`GET /api/v1/agent/onboarding` 返回接入自检包，包含安全状态、部署就绪、能力组、Skill 加载顺序、建议首批调用和 integrity 边界。它公开只读，不执行实验、不读取外部 URI、不返回 OpenAPI 全量正文。

`GET /api/v1/system/security` 返回公开入口、认证方式、保护范围和审计策略。本地开发默认不要求 token；生产部署设置 `AUTORESEARCH_API_TOKEN` 后，非公开 endpoint 必须带 Bearer token。外部 Runtime 只能从部署环境读取 token，不能把 token 写入 session event、source、artifact metadata、review、decision 或 experience。

平台审计只记录 metadata: method、path、status code、actor、认证结果、query key、content type 和 user agent。写操作和被拒绝请求会进入 `logs` collection；平台不会保存请求正文、密钥、大型输出、外部 Runtime 原文或 checkpoint。

## 上下文恢复

`GET /api/v1/research/context?query=...&claim=...` 返回 `counts`、`sections`、`evidence_summary`、`risk_flags` 和 `recommended_next_actions`。外部 Runtime 应先用它判断已有资料、假设、协议、账本、artifact、证据和审查是否已经存在，避免重复写入。它只读，不执行实验，也不会替 Runtime 调用建议动作。

## 就绪检查

`GET /api/v1/research/readiness` 返回 `state`、`checks`、`blocking_gaps`、`warning_gaps`、上下文、轮次追踪包和建议动作。它适合在 `before_experiment`、`before_review`、`before_decision` 和 `before_curation` 阶段调用。返回 `blocked` 时，外部 Runtime 应先补实验、artifact、证据、决策或修复 `unresolved_refs`；平台不会自动执行这些动作。

## 轮次留痕

每个新方案应登记一个 research round。推荐顺序:

1. 外部 Runtime 在自己的环境中创建独立 worktree/branch。
2. `POST /api/v1/research/rounds` 写入 proposal、worktree path、branch、base ref 和可选 session。
3. 外部 Runtime 实现方案、提交 commit、运行实验并登记 artifact。
4. `PATCH /api/v1/research/rounds/{round_id}` 回填 commit、experiment、artifact、evidence 和 decision 引用。
5. `GET /api/v1/research/rounds/{round_id}` 读取追踪包，确认已解析记录、warnings、`unresolved_refs` 和建议动作。

平台不会创建 worktree、执行 git 或读取外部工作目录。`completed` 的 research round 必须包含 commit、experiment、artifact、evidence 或 decision 中至少一种追踪引用。
如果追踪包返回 `unresolved_refs`，外部 Runtime 应先修正引用或登记阻塞/降级状态，不能把该轮作为完整证据沉淀到 decision 或 experience。

## 结果证据

benchmark suite 应先登记外部适配器、输入合同、输出合同、指标合同和成果要求。`GET /api/v1/benchmarks/audit` 返回 `blocked` 时，外部 Runtime 应修复 suite 合同，而不是直接运行评测。

benchmark run 完成且包含 `scores` 时，必须提供 `artifact_refs` 或 `provenance.runner`。大型输出、原文和 checkpoint 必须留在外部存储。

`GET /api/v1/benchmark-runs/compare?benchmark_id=...&metric=...` 返回最佳 run、指标范围、排序列表、状态分布、证据准备缺口和建议动作。它只比较平台内已登记 metadata，不执行评测、不读取外部 artifact。外部 Runtime 应先补齐缺失的 artifact 或 runner provenance，再把最佳、基线或冲突 run 写入 evidence record。

`GET /api/v1/artifacts/audit?session_id=...` 会只读检查 artifact 是否缺少 URI、hash、size、storage 或 summary。它不读取外部 URI，也不下载对象；如果返回 `blocked`，外部 Runtime 应先重新登记完整 artifact 引用，再把它作为证据来源。

evidence record 必须包含 `evidence_refs`。它连接科研主张与支持、反证、不确定或复现证据，是 review 和 decision 之前的机器可读证据层。

`GET /api/v1/evidence-records/summary?claim=...` 会按完整科研主张聚合已完成证据，返回支持、反证、不确定、复现、复现失败、置信度计数、覆盖范围、质量缺口和复现计划建议，并给出确定性的 `recommended_next_action`。它不是最终结论，只是帮助外部 Runtime 决定继续收证、登记复现、补跨 session 证据、排查冲突、进入审查或写入决策。

`GET /api/v1/reviews/audit?q=...` 会只读检查审查事件是否包含被审查对象、reviewer provenance、说明、证据引用、分数或 concerns。它不调用 critic，也不生成结论；如果返回 `blocked`，先补充更完整的 review。

decision record 必须包含 `evidence_refs`。它记录科研判断，不触发实验执行，也不会自动创建长期经验。

`GET /api/v1/research/audit/export?query=...&claim=...&session_id=...&round_id=...` 会导出只读审计包，包含 context、session ledger、round trace、artifact audit、review audit、reproducibility、integrity 和 recommended actions。这个包用于交接、复现和开源审查，不访问外部 URI、不读取 Runtime 工作目录、不执行实验。

`reproducibility` 是交接清单，不是执行计划。外部 Runtime 应读取其中的 checklist、external_artifacts 和 handoff_steps，在自己的环境中验证 artifact URI/hash、补复现实验、修复未解析引用或进入审查/决策。

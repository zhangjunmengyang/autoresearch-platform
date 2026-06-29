# AutoResearch Platform 开源升级计划

## 目标

将 AutoResearch Platform 升级为通用、可开源、可审计、可被外部 Runtime 长期驱动的自动化科研基础设施。平台只保存 REST/OpenAPI 事实源、状态、账本、artifact 引用、显式经验维护和 React 工作台；科研执行、模型调用、评测运行、训练、搜索和 agent loop 均由外部 Runtime 负责。

## 当前判断

已经具备的基础：

- FastAPI 提供资料、洞察、假设、方法论、研究队列、账本、研究轮次、实验、artifact、benchmark、evidence、review、decision 和 experience 的 REST 合同。
- OpenAPI 已带 `x-agent-guidance`、`x-capability-group`、`x-safety-level`、`x-agent-visible` 和 `x-response-contract`。
- React 工作台已经覆盖主要科研对象，并逐步统一为中文产品面。
- 本地 JSON store 可支持开发与 demo，Alembic schema 提供 PostgreSQL 合同雏形。

需要完善的缺口：

- 平台边界需要用白名单合同持续约束，防止为任何举例场景或外部交互形态创建一等模块。
- 科研方法论还需要更强的问题拆解、对照设计、复现实验计划、反证策略、自动 Runtime 恢复协议和每轮研究留痕。
- evidence、review 与 decision 已形成初步链路；已具备主张级证据聚合、质量缺口、覆盖范围、复现计划建议和 review 质量门。
- artifact 需要继续强化引用规则、大小边界、hash、MIME、外部存储位置和禁止内联内容的验证。
- 平台不需要内置科研实体关系推断层；引用追踪应落在研究轮次、证据、决策和 artifact 账本字段中，避免把外部 Runtime 的推理关系内化为平台事实。
- PostgreSQL store adapter、部署模板、认证、审计导出、演示数据和外部 Runtime cookbook 仍需补齐。

## 不做什么

- 不实现 LLM provider router、fallback、限流、成本治理或 key 管理。
- 不实现 benchmark 执行器、模型训练、架构搜索或 agent loop。
- 不直接读写外部 Runtime 的工作目录、数据库或临时脚本。
- 不恢复旧式 workflow DAG、自动经验抽取或 embedding/RAG 原文表。
- 不为举例场景创建平台内一等模块；外部输入只能被规约为通用 source、session event 或 artifact reference。

## 阶段计划

### P0：边界与合同

- 使用 OpenAPI capability group 白名单约束公开能力。
- 使用前端路由与导航白名单约束工作台入口。
- 确保每个公开 endpoint 都有 agent metadata。
- 保持 `blocked`、`degraded` 作为合法状态，不伪造结论。

### P1：科研闭环

- 已补齐证据记录：`POST /api/v1/evidence-records` 与 `GET /api/v1/evidence-records`。
- 已补齐主张级证据概览：`GET /api/v1/evidence-records/summary?claim=...`。
- 已补齐研究上下文恢复包：`GET /api/v1/research/context?query=...&claim=...`。
- 已补齐决策记录：`POST /api/v1/decisions` 与 `GET /api/v1/decisions`。
- 证据与决策都必须引用 `evidence_refs`，工作台已接入“证据记录”和“决策记录”。
- 外部 Runtime 文档和 Skill 默认采用 experience query -> research context -> benchmark/artifact -> evidence -> evidence summary -> review -> decision -> curation。

### P1.5：研究轮次留痕

- 已补齐 proposal/round 级账本，记录每一轮方案、分支或 worktree 引用、commit 引用、实验、artifact、证据和决策。
- 平台只保存引用和状态，不创建 worktree、不提交代码、不读写外部 Runtime 工作目录。
- Skill 负责指导外部 Agent 在新方案中创建 worktree、实现、提交、登记实验和回填 round ledger。

### P2：证据与 artifact 治理

- 强化 artifact 引用合同：URI、hash、MIME、大小、存储位置、摘要和读取提示。
- 拒绝原文、二进制、大型媒体、checkpoint、大型 benchmark 输出等内联内容。
- 已补齐 artifact 元数据审计：`GET /api/v1/artifacts/audit` 返回缺 URI、hash、大小、摘要等缺口和修复动作。
- 已为 benchmark completion 增加 artifact 或 runner provenance 的硬约束。
- 已为 evidence 增加支持、反证、不确定、复现、置信度、覆盖范围、质量缺口和复现计划建议的确定性聚合。
- 已补齐 review 质量门：`GET /api/v1/reviews/audit` 审计 reviewer provenance、comments、evidence_refs、score/concerns。
- 下一步强化经验治理视图和 research context 对引用链的只读恢复。

### P3：经验生命周期

- 完整落地 experience curation 的 create、update、reject、supersede 和 topic_summary。
- preview 返回可读 warning，apply 必须引用 source_refs。
- 经验不能从 session 自动生成，只能由外部 Runtime 显式提交候选并保留证据链。

### P4：上下文恢复与检索

- 强化 `GET /api/v1/research/context` 的检索质量，围绕问题、主张、状态、artifact 和经验做只读上下文恢复。
- 将 research round、evidence、decision、review、benchmark、artifact 与 experience 的显式引用纳入上下文包，而不是生成隐藏关系推断层。
- 增加冲突证据、复现缺口、阻塞状态和缺失 artifact 的可解释提示。

### P5：开源工程化

- 完善 README、CONTRIBUTING、SECURITY、LICENSE、Docker Compose、`.env.example` 和 demo seed。
- 提供 Runtime cookbook、HTTP 请求示例和最小接入流程。
- 增加 `make verify-release`，串联后端测试、前端静态合同、类型检查和 OpenAPI 生成。
- 补齐 PostgreSQL store adapter 与部署文档。

## 验证门

每次涉及合同、前端入口或文档的改动至少运行：

```bash
make test
make openapi
```

发布前运行：

```bash
make verify-release
```

## 后续优先级

1. 补齐研究轮次留痕：方案、worktree/branch、commit、实验、artifact、证据和决策引用。
2. 强化经验治理视图。
3. 强化 research context 对 evidence/review/decision 引用链的只读恢复。
4. 浏览器验证关键页面，确认中文文案、创建流程和列表渲染正常。
5. 推进 PostgreSQL adapter、认证与审计导出。

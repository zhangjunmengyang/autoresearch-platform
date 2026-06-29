# Boundary Rules

## 平台负责

- REST/OpenAPI 合同和 agent metadata。
- 资料、insight、任务、账本、artifact 引用、benchmark run、review、通用 Runtime 事件和长期经验。
- React 工作台展示和轻量创建/更新操作。
- Alembic schema 合同和 guardrail 测试。

## 外部 Runtime 负责

- 模型调用和 agent loop。
- benchmark 执行、训练、评测和架构搜索。
- 论文解析、代码执行、实验执行和 report 生成。
- 任意具体交互形态、提醒系统、聊天界面、监控器或 IDE 自动化。
- 从 ledger/artifact/人工指令中显式生成 experience curation payload。

## 禁止

- 平台自动从 session 生成长期经验。
- 将大 PDF、音频、视频、checkpoint 或大 benchmark 输出写入 DB。
- 为了单次研究添加临时脚本入口。
- 在后端恢复旧式 workflow DAG 或 embedding/RAG 原文表。
- 为举例场景创建一等模块；平台只保存通用 sources、session events 和 artifact references。

## Artifact 与 Runtime Event

Artifacts 是引用，不是 blob storage。大型文档、媒体、checkpoint、原始外部输入、benchmark dump 和生成报告都保留在外部存储中，只能以 URI、hash、MIME、大小、存储位置和摘要进入平台。Artifact audit 只能审计平台内 metadata 是否齐全，不访问 URI、不读取外部存储。

Runtime event 是通用账本条目。平台不得推断、建模或固化产生事件的外部交互形态。

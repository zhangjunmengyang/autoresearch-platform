# Migration From quant-platform-pro

本项目抽取了 quant-platform-pro 的研究账本、研究队列、经验显式维护和 OpenAPI agent metadata 模式。

## 已抽取

- Research session ledger 的 session、event、experiment、artifact、close 语义。
- Research intake 的任务提交、领取和启动 session 语义。
- Experience Hub 的 query、curation preview、curation apply 语义。
- OpenAPI `x-agent-*` 元数据和 REST-first 外部 Runtime 合同。
- React 工作台的浅色、侧边栏、表单、列表和状态展示模式。

## 未抽取

- 量化因子、策略、交易、DCA、外部回测引擎和行情数据。
- Graph Hub 的实体关系图模式。
- 旧式 research runtime DAG。
- 平台内模型调用、公共工具协议、脚本式同步和 embedding/RAG 原文表。

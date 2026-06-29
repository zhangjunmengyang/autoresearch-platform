# 贡献指南

感谢参与 AutoResearch Platform。这个项目维护的是通用自动化科研基础设施，不是外部 Runtime。

## 开发前提

- 文档、注释和工作台可见文案使用中文。
- 不使用 emoji。
- 改动后至少运行 `make test` 和 `make openapi`。
- 修改公共 endpoint 时，必须确认 OpenAPI 里保留五个 agent metadata 字段。

## 边界要求

不要向平台加入:

- Runtime 执行、模型路由、benchmark 运行、训练、架构搜索或 agent loop。
- 具体场景的一等交互通道。
- 外部 Runtime 工作目录、数据库或临时脚本的直接读写。
- 原文、大 artifact、checkpoint、benchmark dump 或媒体内容存储。
- 自动经验抽取、旧式 workflow DAG、embedding/RAG 原文表。

## 推荐流程

1. 先读 `AGENTS.md`、`docs/architecture/reference.md` 和 `docs/architecture/external-runtime-api.md`。
2. 用测试表达 API 合同变化。
3. 实现最小必要改动。
4. 运行验证并重新生成 `docs/openapi.json`。
5. 在 PR 中说明平台边界是否发生变化。

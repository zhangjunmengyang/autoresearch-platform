# 安全策略

AutoResearch Platform 当前定位为本地和内网科研基础设施。生产部署需要由部署方配置认证、网络边界、日志保留、备份、密钥管理和 CORS。

平台提供一个最小部署边界: 设置 `AUTORESEARCH_API_TOKEN` 后，非公开 API endpoint 要求 `Authorization: Bearer <token>`。未设置 token 时保持本地开发模式，`GET /api/v1/system/security` 会报告认证未启用。这个 token 只用于保护平台 REST 接口，不承担 LLM provider key 管理、租户隔离或细粒度权限控制。

## 范围内

- REST/OpenAPI endpoint 的输入校验和状态合同。
- 可选 Bearer token 保护非公开 API endpoint。
- 写操作和被拒绝请求的 metadata-only 审计账本。
- artifact 引用边界，避免把大文件、原文、媒体或 checkpoint 写入平台 DB。
- `blocked`、`degraded`、`rejected` 等状态的诚实记录。
- PostgreSQL 连接字符串、CORS origins 等部署配置的显式化。

## 范围外

- LLM provider key 管理、模型调用审计、成本治理和限流。
- 外部 Runtime 的 sandbox、agent loop、benchmark runner 和训练环境安全。
- 部署平台的反向代理、TLS、WAF、密钥轮换、细粒度权限和备份策略。

## 审计边界

平台审计只记录请求方法、路径、状态码、actor、认证结果、query key、content type 和 user agent 等元数据。平台不得把请求正文、Bearer token、LLM provider key、大型 artifact、外部 Runtime 原文或 checkpoint 写入审计账本。

## 报告问题

请在 issue 或私有安全渠道中提供:

- 影响的 endpoint 或部署配置。
- 可复现请求。
- 期望行为和实际行为。
- 是否涉及数据泄露、权限绕过或持久化破坏。

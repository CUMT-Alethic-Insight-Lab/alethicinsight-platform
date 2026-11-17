# 内部成员平台 MVP 手册：兼容导航

本路径仅为旧链接保留。内部成员平台已从原 `member-platform/` 子树提取到独立仓；安装、配置、运行、权限、CLI/MCP 与验收以[新成员仓 README](https://github.com/CUMT-Alethic-Insight-Lab/alethicinsight-member-platform#readme)及其文档为准，本仓不再维护成员运行手册副本。

- CLI 与本地 stdio MCP 仍是同一个 `alethicinsight-cli` 包，入口 `alethicinsight-cli`、`alethicinsight-mcp` 不改，归成员仓内部 infra。
- 不从考试仓安装成员工具，不复用考试 `/recruitment`、账号、会话、数据库或凭据。最终事务提交仍须本人在可信成员网页确认。
- 新仓发布与验证完成前不应合并本拆仓 PR；本地提取不是远端发布、生产部署或真实数据迁移的证明。旧成员 API 公网入口继续默认 503，不因文档导航启用。

相关：[成员旧文档索引](agent-interface/README.md)、[产品边界](REPOSITORY_BOUNDARIES.md)、[隔离与分仓历史](migration.md)、[考试部署兼容](../server/deploy/README.md)。

# 内部成员接口体系：兼容导航

内部成员产品的源码、设计、API 契约与使用手册归独立的 [alethicinsight-member-platform](https://github.com/CUMT-Alethic-Insight-Lab/alethicinsight-member-platform)。请从[新仓 README](https://github.com/CUMT-Alethic-Insight-Lab/alethicinsight-member-platform#readme)进入其当前文档；本目录仅保留旧 Markdown 文件路径，不维护第二份详细设计或 YAML 契约。

CLI/MCP 同包同版本，仍属新成员仓内部 infra，不另拆 MCP 仓、不改命令。考试 `server/` 不提供成员 `/org` 或 `/api/v1`，不复用两产品账号、DB 或会话。旧成员 API 公网入口继续默认 503，见[考试部署说明](../../server/deploy/README.md)。

## 旧路径索引

以下各页均为短导航，不再作为考试仓开发任务或成员权威契约：

- [00 · 历史审查](docs/00-current-system-review.md)
- [01 · 产品与用户故事](docs/01-product-and-user-stories.md)
- [02 · 架构](docs/02-architecture.md)
- [03 · 认证与权限](docs/03-auth-and-permissions.md)
- [04 · API 与工作流](docs/04-api-and-workflows.md)
- [05 · CLI/MCP/Skill](docs/05-cli-mcp-skills.md)
- [06 · 数据模型与集成](docs/06-data-model-and-integrations.md)
- [07 · 运维方案](docs/07-deployment-ops.md)
- [08 · 安全隐私](docs/08-security-privacy.md)
- [09 · 验收](docs/09-roadmap-and-acceptance.md)
- [10 · 决策](docs/10-decision-register.md)
- [11 · Agent 交接](docs/11-agent-handoff.md)
- [12 · 参考与兼容](docs/12-references-and-compatibility.md)
- [契约导航（原 YAML 已移除）](contracts/README.md)
- [org-access 旧 Skill 路径](skills/org-access/SKILL.md)
- [CLI 示例旧路径](examples/cli-usage.md)
- [MVP 手册旧路径](../AGENT_INTERFACE_MVP.md)

PR #6（`9dc7229`）已完成第一阶段同仓隔离；当前本地从成员子树保留历史提取独立仓，本分支删除考试仓重复源码。**新仓发布与验证完成前不应合并本拆仓 PR。** 这里给出目标导航，不声称远端已发布、生产已部署或真实数据已迁移。历史和工作边界见[迁移记录](../migration.md)、[产品职责](../REPOSITORY_BOUNDARIES.md)与[工作区保全](../WORKSPACE_MIGRATION.md)。

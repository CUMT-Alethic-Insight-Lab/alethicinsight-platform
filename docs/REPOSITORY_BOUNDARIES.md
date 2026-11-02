# 仓库职责与公开边界

本页记录已确定的整理边界，不授权迁移目录、创建远程仓库、推送或生产部署。工作区操作按[迁移清单](WORKSPACE_MIGRATION.md)另行人工执行。

## 公共接口归 infra

- CLI 与本地 stdio MCP 同属 infra 的公共接口，不属于私有运维交接材料。
- 统一路径：`infra/interface/alethicinsight-cli/`。单仓、单发行包、单版本，正式发行名 `alethicinsight-cli`；命令入口为 `alethicinsight-cli` 与 `alethicinsight-mcp`。
- 不保留两个顶层产品目录，不新建独立 MCP 仓，不分别发布两套版本。协议适配与命令入口可以在包内模块隔离。
- 共享稳定 REST 契约，MCP 调用同包 CLI；客户端不得直接读业务数据库。既有 `/api/v1/auth/cli/*` 授权 API 路由不因产品改名而变更。
- 新客户端配置使用 `ALETHICINSIGHT_API_BASE_URL`、`ALETHICINSIGHT_CONFIG_DIR`。旧 `ALETHIC_API_BASE_URL`、`ALETHIC_BASE_URL`、`ALETHIC_CONFIG_DIR` 仅作兼容别名，不在新示例中推荐；服务端现有 `ALE_THIC_*` 配置不在本次客户端重命名范围。
- 查询、校验与草稿可经 CLI/MCP；正式提交只能由成员在可信网页核对确认。CLI/MCP 不授予管理员审批能力，不替代服务端成员资格、scope 和资源 ACL 校验。

## 私有资料与业务数据

| 位置/仓库 | 职责 | 禁止事项 |
|---|---|---|
| infra 公共代码与接口文档 | 可审查的实现、协议、合成夹具、本地脱敏示例 | 不存真实凭据、成员数据、考生记录、私有主机清单或生产日志 |
| `infra-handoff` | 私有运维交接：主机/账号信息、密钥位置、访问与恢复流程、排障记录 | 不承载公共 CLI/MCP 产品源码或成为其发行源 |
| `question-bank` | 私有真实题库与解析 | 不将真实试题复制进公共测试夹具 |
| `exam-archive` | 受控考生活档与附件 | 清洗件仍可能含个人信息，不因“已清洗”而公开 |
| `governance-public` | 已审核公开章程与规则 | 不由 Agent 对话自行改写制度 |
| `open-onboarding` / `awesome-ai` | 公开上手说明与学习索引 | 不保存成员权限、内部事务或凭据 |

凭据应留在受控秘密管理位置；私有仓也不是把明文密钥提交 Git 的理由。数据库、WAL、上传、会话、备份、截图和日志须按真实数据处理，不因目录改名或复制而降低保护等级。公开前审查内容及历史，发现泄密先停公开并由负责人处理撤销/轮换；不要靠删除当前文件宣称历史已净化。

## 本次不改的边界

- `Alethic-Insight-Frontend-Templates` 完全不碰：不编辑、不移动、不调整仓库职责。
- `E:/projects/Aletheion` 仅为历史来源，不作为 monorepo；其中可复用材料也需单独确认来源、许可、提交状态和敏感性。
- 保持现有 `server/`、`exam_kit/` 的业务职责；本次不建议立刻拆 exam-kit，也不以整理为由迁移真实数据或部署生产。
- P: / E: 本地位置不等于远程仓库职责。先保护未提交与未跟踪内容，再确定目标仓和工作副本；不直接合并整个历史目录。

相关入口：[根 README](../README.md)、[本地 MVP 手册](AGENT_INTERFACE_MVP.md)、[接口架构](agent-interface/docs/02-architecture.md)。

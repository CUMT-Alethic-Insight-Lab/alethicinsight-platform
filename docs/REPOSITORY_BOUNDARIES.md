# 产品职责、仓库布局与公开边界

## 两个独立产品，第一阶段同仓隔离

内部成员平台与招新筛选不是一个产品。已撤销“在招新平台上增量扩展成员事务、共享账号和数据库”的方案。共同基线 `229e69c` 的组织接口实际与考试共用 DB、账号和启动流程；本页是隔离 PR 的审查边界，不是只改目录名便已解耦的声明。

| 位置 | 职责 | 运行边界 |
| --- | --- | --- |
| 根 `server/` | 招新报名、问卷、考试、评审、交卷与归档 | 自己的进程、考试 DB、考生/管理账号、会话、配置与生命周期；不挂载组织业务 |
| `member-platform/server/` | 内部成员、项目、知识与事务 | 自己的进程、成员 DB、账号、网页会话、grant 与权限；不加载考试任务/数据 |
| `member-platform/infra/interface/alethicinsight-cli/` | 内部产品 CLI 与本地 stdio MCP | 同包同版本，通过成员 REST，不直接读 DB |
| `docs/agent-interface/` | 成员产品设计、契约与安全约束 | 不再指示在根考试服务中新增组织接口 |
| 独立 [recruitment-exam-kit](https://github.com/CUMT-Alethic-Insight-Lab/recruitment-exam-kit) | 考生本地机试、清洗、LAN 接收机、安装器 | 已有独立源码权威，不恢复本仓 `exam_kit/` |

上述是第一阶段同仓布局，不是最终分仓。先完成隔离代码、双进程空库/合成账号测试、契约与安装验证，提交 PR 审查；再决定独立仓映射与远端名。`alethicinsight-platform` 是历史误改名，这次不重命名、不编造新仓 URL。生产部署、真实成员账号/记录迁移均未执行，且不是文档变更可以证明的事。

## 内部 infra 的接口边界

- CLI/MCP 正式发行名 `alethicinsight-cli`，入口 `alethicinsight-cli` 与 `alethicinsight-mcp`。单发行包、单版本，不另建 MCP 仓。
- API 名保持 `/api/v1/auth/cli/*`、项目/知识/申请等现有契约，不以代码移动为由改名。显式成员服务根例为 `http://localhost:8902`，CLI base 不含 `/api/v1`，不使用考试 `/recruitment`。
- 新客户端变量 `ALETHICINSIGHT_API_BASE_URL`、`ALETHICINSIGHT_CONFIG_DIR`；旧 `ALETHIC_API_BASE_URL`、`ALETHIC_BASE_URL`、`ALETHIC_CONFIG_DIR` 只兼容。相同变量名不意味着可以复用两个产品的配置值或凭据。
- 查询、校验、草稿可经 CLI/MCP；正式提交在可信成员网页确认。当前成员资格、scope、资源 ACL 逐请求检查；CLI 不继承管理员 review 权限。考试管理员也不自动成为成员平台管理员。

## 私有资料与业务数据

| 位置/仓库 | 职责 | 禁止事项 |
| --- | --- | --- |
| 成员 infra 公共源码/契约 | 可审查实现、合成夹具、本地脱敏示例 | 不存凭据、成员/考生资料、生产日志 |
| `infra-handoff` | 私有运维交接、主机/账号与恢复说明 | 不承载 CLI/MCP 产品源码，不把私有仓当明文密钥库 |
| `question-bank` | 私有真实题库与解析 | 不复制到公共测试夹具 |
| `exam-archive` | 受控考生清洗件和附件 | 清洗不等于公开授权 |
| `recruitment-materials` | 受控招新物料 | 不随源码隔离公开真实材料 |
| `governance-public` | 已审核公开章程与规则 | Agent 不能自行改写制度 |
| `open-onboarding` / `awesome-ai` | 公开上手与学习索引 | 不保存成员权限和凭据 |

数据库/WAL、上传、会话、备份、截图与日志按真实数据保护，移动目录不能降低保护等级。公开前审查内容及历史；发现泄密先停止公开并由负责人撤销/轮换，不能删除当前文件便宣称历史净化。本次不读取秘密、不迁移真实账号或 DB。

## 工作区与排除项

- `Alethic-Insight-Frontend-Templates` 完全不碰，不编辑、移动或调整职责。
- `E:/projects/Aletheion` 仅为历史来源，不作为 monorepo；不批量搬入历史目录。
- 不触碰原脏主仓，不覆盖不同 HEAD 的副本；不用 reset/clean 消除差异。不因 worktree 共享 Git 对象便将它视为完整备份。
- 本地路径不等于远端产品职责；第一阶段之后才审议独立仓/远端映射。详见[工作区保全](WORKSPACE_MIGRATION.md)。

相关入口：[根 README](../README.md)、[成员平台](../member-platform/README.md)、[运行手册](AGENT_INTERFACE_MVP.md)、[历史与迁移门禁](migration.md)。

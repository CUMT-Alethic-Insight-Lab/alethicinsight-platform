# 产品职责、仓库布局与公开边界

## 当前分仓：招新筛选与内部成员是独立产品

招新筛选服务考生与评审，内部成员平台服务认证成员；不是通用平台的前后阶段。PR #6 已合并（`9dc7229`），第一阶段同仓隔离成为历史基线。本次将原 `member-platform/` 子树保留历史提取到独立成员仓，本分支移除考试仓重复源码；不再把同仓目录当作最终归属。`main` 仍保留成员副本，去重待 [PR #7](https://github.com/CUMT-Alethic-Insight-Lab/recruitment-exam-platform/pull/7) 审查合并；仓库名恢复不代表去重已合入。

| 位置/仓库 | 职责 | 运行边界 |
| --- | --- | --- |
| 本仓 [recruitment-exam-platform](https://github.com/CUMT-Alethic-Insight-Lab/recruitment-exam-platform) 的 `server/` | 招新报名、问卷、考试、评审、交卷与归档 | 考试进程、DB、考生/管理账号、会话、配置与生命周期；不挂载组织业务。仓库名已获授权恢复 |
| 独立 [alethicinsight-member-platform](https://github.com/CUMT-Alethic-Insight-Lab/alethicinsight-member-platform) | 原成员子树的 server、infra 与成员文档 | 独立成员进程、DB、账号、网页会话、grant 与权限；不加载考试任务/数据 |
| 成员仓 `infra/interface/alethicinsight-cli/` | 内部产品 CLI 与本地 stdio MCP | 同包同版本，通过成员 REST，不直接读 DB，不另建 MCP 仓 |
| 本仓 `docs/agent-interface/`、`docs/AGENT_INTERFACE_MVP.md` | 旧 URL 的精简兼容导航 | 不维护成员详细设计或 YAML 契约副本，不指示在考试服务新增组织接口 |
| 独立 [recruitment-exam-kit](https://github.com/CUMT-Alethic-Insight-Lab/recruitment-exam-kit) | 考生本地机试、清洗、LAN 接收机、安装器 | 已有独立源码权威；本次不改，不恢复本仓 `exam_kit/` |

成员仓已在本地从子树保留历史准备，远端发布及其验证由负责人执行；本文不声称已发布。**新成员仓发布与验证完成前，不应合并本拆仓 PR。** 原源码仍可在本仓 `9dc7229` 历史基线及成员独立副本中追溯。本次仅移除跟踪的重复源码，不清除数据，不证明生产部署或真实成员迁移完成。

## 兼容接口与内部 infra 边界

- 考试 `/api/auth/*`、`/api/campaigns/*`、exam-kit 协议及 edge/authoritative 部署兼容不变，不因拆仓改命令。
- 旧成员 API 公网入口 `/recruitment/api/v1`（含子路径）在考试 nginx 模板中继续默认 **503（fail closed）**，不回源或回落到考试进程。独立成员上游须另行审批、显式配置；本次不启用、不部署。详见[考试部署说明](../server/deploy/README.md)。
- CLI/MCP 正式发行名 `alethicinsight-cli`，入口 `alethicinsight-cli` 与 `alethicinsight-mcp` 保持不变。成员 API 保持 `/api/v1/auth/cli/*` 等现有契约，不因代码提取改名。
- 成员服务根与凭据由新仓手册指导；不能使用考试 `/recruitment`、考试会话或历史凭据来绕过隔离。相同登录 API 拼写不意味着身份源相同。
- 查询、校验、草稿可经 CLI/MCP；正式提交由成员在可信网页确认，管理员 review 也只在成员网页。考试管理员不自动成为成员管理员。

## 私有资料与业务数据

| 位置/仓库 | 职责 | 禁止事项 |
| --- | --- | --- |
| 成员 infra 公共源码/契约 | 可审查实现、合成夹具、本地脱敏示例 | 不存凭据、成员/考生资料、生产日志 |
| `infra-handoff` | 私有运维交接、主机/账号与恢复说明 | 不承载 CLI/MCP 产品源码，不把私有仓当明文密钥库 |
| `question-bank` | 私有真实题库与解析 | 不复制到公共测试夹具 |
| `exam-archive` | 受控考生清洗件和附件 | 清洗不等于公开授权 |
| `recruitment-materials` | 受控招新物料 | 不随源码提取公开真实材料 |
| `governance-public` | 已审核公开章程与规则 | Agent 不能自行改写制度 |
| `open-onboarding` / `awesome-ai` | 公开上手与学习索引 | 不保存成员权限和凭据 |

数据库/WAL、上传、会话、备份、截图与日志按真实数据保护，源码分仓不能降低保护等级。公开前审查内容及提取后的历史；保留历史不代表历史已经脱敏。发现泄密先停止公开并由负责人撤销/轮换，不能删除当前文件便宣称历史净化。本次不读取秘密、不迁移真实账号或 DB，不删除旧表或存档。

## 工作区与排除项

- `Alethic-Insight-Frontend-Templates` 完全不碰，不编辑、移动或调整职责。
- `E:/projects/Aletheion` 仅为历史来源，不作为 monorepo；不批量搬入历史目录。
- 不触碰原脏主仓，不覆盖不同 HEAD 的副本，不用 reset/clean 消除差异。worktree 共享 Git 对象，不是完整独立备份。
- 本地路径不等于远端发布或生产状态。保全、发布前核验及回退要求见[工作区保全](WORKSPACE_MIGRATION.md)。

相关入口：[根 README](../README.md)、[成员仓](https://github.com/CUMT-Alethic-Insight-Lab/alethicinsight-member-platform)、[旧成员文档导航](agent-interface/README.md)、[历史与迁移门禁](migration.md)。

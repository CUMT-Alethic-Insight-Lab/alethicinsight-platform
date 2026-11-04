# Alethic Insight · 招新筛选与内部成员平台

这里维护两个独立产品的第一阶段同仓隔离代码：**招新筛选**服务考生与招新评审；**内部成员平台**服务认证成员的知识查询、项目目录与事务申请。二者不是同一平台的前后阶段，也不共享运行中的账号、数据库、会话或管理员权限。

| 产品 | 源码与入口 | 用途 |
| --- | --- | --- |
| 招新筛选 | `server/` | 报名、问卷、面试评审、题库抽题、交卷暂存转发、报告重建与归档 |
| [内部成员平台](member-platform/README.md) | `member-platform/server/` | 成员身份、项目、知识、事务申请与可信网页确认 |
| [成员平台 infra](member-platform/infra/README.md) | `member-platform/infra/interface/alethicinsight-cli/` | 同包同版本的 CLI 与本地 stdio MCP，不属于考试客户端 |
| [recruitment-exam-kit](https://github.com/CUMT-Alethic-Insight-Lab/recruitment-exam-kit) | 独立仓库 | 考生端启动器、本地机试服务、会话清洗、LAN 接收机与安装器 |

同仓目录隔离不是最终分仓。纠正 PR 的代码隔离、双服务回归与 PR 审查仍是交付门禁；文档本身不能证明已经解耦。当前远端名 `alethicinsight-platform` 来自历史误改名，本次不重命名，也不指定新的成员平台仓库 URL。事实、历史与待执行事项见 [产品边界](docs/REPOSITORY_BOUNDARIES.md)和[迁移记录](docs/migration.md)。

## 招新筛选：安装与本地启动

使用 Python 隔离环境；下面从仓库根在 Git Bash/Linux shell 执行，只初始化新的本地开发数据库：

```sh
python -m venv .venv-exam
# Windows Git Bash；Linux 使用 source .venv-exam/bin/activate
source .venv-exam/Scripts/activate
python -m pip install -r server/requirements.txt
export ALE_THIC_DATA_DIR="$PWD/.local-exam"
export ALE_THIC_DB_PATH="$ALE_THIC_DATA_DIR/exam.db"
export ALE_THIC_ROLE=authoritative
export ALE_THIC_CAPTCHA_ENABLED=0
export PUBLIC_PREFIX=''
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
python -m uvicorn app.main:app --app-dir server --host 127.0.0.1 --port 8901
```

访问 `http://127.0.0.1:8901/`；健康检查为 `/api/health`，管理端为 `/admin`。验证码关闭和临时密钥仅供本地开发，不用于上线。初始化账号及密码变更遵循应用提示，不复制生产账号。

招新系统保留 `/api/auth/*`、`/api/campaigns/*`、考试与交卷兼容协议，**根 `server` 不承担成员 `/org` 与 `/api/v1` 组织接口**。已有 edge 暂存转发、authoritative 收口和考试归档均属于本产品；部署脚本说明见 [server/deploy/README.md](server/deploy/README.md)，不是成员平台部署入口。

## 内部成员平台：独立安装与使用

在另一个终端、另一个虚拟环境中按 [成员平台 README](member-platform/README.md) 启动 `member-platform/server`，本地示例服务根为 **`http://localhost:8902`**，网页入口为 `/org`。CLI/MCP 从成员平台自己的 infra 安装，显式设置服务根，不使用考试 `/recruitment` 地址：

```sh
python -m pip install ./member-platform/infra/interface/alethicinsight-cli
export ALETHICINSIGHT_API_BASE_URL=http://localhost:8902
# 登录前另设仓库外全新私有 ALETHICINSIGHT_CONFIG_DIR，见成员平台手册
alethicinsight-cli --help
alethicinsight-mcp --help
```

成员网页会话只对成员服务有效；CLI 一次性 code 换取短时、可撤销 grant，不复制网页 token。CLI/MCP 只查询、校验与准备草稿，最终提交必须由成员在可信网页确认；管理员 review 也只在成员平台网页进行。详见 [本地运行手册](docs/AGENT_INTERFACE_MVP.md)。

### 两套运行边界

| 边界 | 招新筛选 | 内部成员平台 |
| --- | --- | --- |
| 本地进程/端口 | `server`，8901 | `member-platform/server`，8902 |
| 本地数据示例 | `.local-exam/exam.db` | `.local-member/member.db` |
| 账号与会话 | 考生/招新管理账号及会话 | 成员本地账号、网页会话和 CLI grant |
| 权限 | 招新报名、考试、评审门禁 | member/admin、scope、资源 ACL、可信网页确认 |
| 生命周期 | 按招新批次、清洗件与考试归档策略 | 按成员、项目、事务、知识与审计策略 |

不得把两个进程指向同一个 SQLite 文件或复制对方的会话/凭据。即使配置键名或 API 登录路径相同，也不代表共享身份源。既有真实成员账号如何从历史混合库迁出尚待单独审批与验证；本次不迁移真实数据、不部署生产。

## 开发与验证

服务端使用 FastAPI + SQLite + 原生 HTML/JS，无额外前端构建。分别在对应虚拟环境中执行：

```sh
(cd server && python -m pytest tests -q)
(cd member-platform/server && python -m pytest tests -q)
python -m pip wheel --no-deps ./member-platform/infra/interface/alethicinsight-cli --wheel-dir /path/to/new-temporary-wheel-dir
```

这些是验证命令，不是本次运行通过的声明。页面 JavaScript 回归需要 Node.js；缺少时相关用例可能跳过，须记录原因。集成还需验证：双服务同时运行、考试不挂载组织路由、两个空库与账号互不影响、跨服务 token 拒绝，以及合成数据 CLI/MCP 闭环。完整验收见 [交付门禁](docs/agent-interface/docs/09-roadmap-and-acceptance.md)。

## 考生隐私、下载与版本兼容

考生在自己的电脑使用 AI 工具，由独立 [exam-kit](https://github.com/CUMT-Alethic-Insight-Lab/recruitment-exam-kit#readme) 导出并清洗指定会话，只上传去除思考过程与工具输出正文的清洗件。招新服务处理已提交的清洗件，不远程读取考生文件。`server/app/cleaned_report.py` 重建评审 Markdown。

- 安装器、构建与清洗测试以 [套件 README](https://github.com/CUMT-Alethic-Insight-Lab/recruitment-exam-kit#readme) 为准；下载与 SHA256 以 [Releases](https://github.com/CUMT-Alethic-Insight-Lab/recruitment-exam-kit/releases) 为准。
- `server/static/kit-version.json` 只是考试客户端 OTA 兼容元数据，更新必须对应已验证的安装包 URL、版本与 SHA256。
- 不宣称任意两个最新版兼容。联动发布须记录考试服务 commit/tag、套件 commit/tag、安装包版本/SHA256，并用该组合验证登录、题目、清洗交卷、暂存转发及报告下载；LAN/P2P 通路分别验证。

## 文档与相关项目

- [产品职责与公开边界](docs/REPOSITORY_BOUNDARIES.md)、[历史与第一阶段迁移门禁](docs/migration.md)、[工作区保全清单](docs/WORKSPACE_MIGRATION.md)
- [内部成员接口契约](docs/agent-interface/README.md)、[本地运行与权限说明](docs/AGENT_INTERFACE_MVP.md)
- [join-us](https://github.com/CUMT-Alethic-Insight-Lab/join-us)：招新流程与下载入口
- [open-onboarding](https://github.com/CUMT-Alethic-Insight-Lab/open-onboarding)：入组练手与贡献流程

公开 Git 只放代码、通用模板和合成夹具。真实题库归 `question-bank`，考生归档归 `exam-archive`，私有运维交接归 `infra-handoff`，招新物料归 `recruitment-materials`；它们的存在不是读取秘密或迁移真实数据的授权。`Alethic-Insight-Frontend-Templates` 不在本次范围。

## License · 许可与归属

CUMT Alethic Insight Lab。页面中的招新素材版权归实验室所有。

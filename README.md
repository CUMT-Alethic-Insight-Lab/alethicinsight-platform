# Alethic Insight · 招新筛选服务端

本仓维护面向考生与招新评审的**招新/筛选服务端**：报名、问卷、面试评审、题库抽题、交卷暂存转发、报告重建与归档。它不是通用成员平台，也不是内部成员产品的前置阶段。

| 产品 | 源码权威与用途 |
| --- | --- |
| 招新筛选服务端（本仓） | `server/`；当前仓库名 `alethicinsight-platform` 暂时保留，不在本次重命名 |
| [内部成员平台](https://github.com/CUMT-Alethic-Insight-Lab/alethicinsight-member-platform) | 独立仓库；成员身份、项目、知识、事务申请与可信网页确认。CLI/MCP 同包归其内部 infra，不属于考试客户端 |
| [recruitment-exam-kit](https://github.com/CUMT-Alethic-Insight-Lab/recruitment-exam-kit) | 已独立的考生端启动器、本地机试服务、会话清洗、LAN 接收机与安装器；本次不修改 |

PR #6 已合并至 `9dc7229`，完成第一阶段同仓隔离。此次从该基线将原 `member-platform/` 子树保留历史提取到独立成员仓，本分支删除考试仓的重复源码，仅保留旧文档路径的兼容导航。**成员新仓发布与验证完成前，不应合并本拆仓 PR。** 独立仓本地准备不等于远端已发布，更不代表生产部署或真实数据迁移。详见[产品边界](docs/REPOSITORY_BOUNDARIES.md)和[迁移记录](docs/migration.md)。

## 安装与本地启动

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

## 考试兼容与部署边界

- `server/` 保留 `/api/auth/*`、`/api/campaigns/*`、考试与交卷兼容协议，不承担成员 `/org` 与 `/api/v1` 组织接口。
- 历史考生账号资料兼容不是内部成员身份源；两产品不共用数据库、运行账号、会话或管理员权限，不把两个进程指向同一 SQLite 文件，也不复制凭据。
- 既有 edge 暂存转发、authoritative 收口与考试归档均属于本产品；[部署说明](server/deploy/README.md)只用于考试服务，不是成员产品部署入口。本次不改变部署协议或命令。
- 旧成员 API 公网地址 `/recruitment/api/v1`（含子路径）在现有 nginx 模板中继续默认 **503（fail closed）**，不回源或回落到考试进程。独立成员上游及其发布须另行审批；本次不启用、不重定向、不部署。

成员安装、服务配置和 CLI/MCP 使用请从[新成员仓 README](https://github.com/CUMT-Alethic-Insight-Lab/alethicinsight-member-platform#readme)进入；本仓不再提供成员安装命令或维护成员契约副本。旧[成员文档目录](docs/agent-interface/README.md)和[运行手册路径](docs/AGENT_INTERFACE_MVP.md)仅作兼容导航。

## 开发与验证

服务端使用 FastAPI + SQLite + 原生 HTML/JS，无额外前端构建。在考试虚拟环境、仓库根运行标准测试：

```sh
python -m pytest server/tests -q
```

页面 JavaScript 回归需要 Node.js；缺少时相关用例可能跳过，应记录原因。成员服务和 CLI/MCP 的测试、打包、合成数据闭环在新成员仓验证，不再从本仓执行；测试通过不代表生产迁移完成。

## 考生隐私、下载与版本兼容

考生在自己的电脑使用 AI 工具，由独立 [exam-kit](https://github.com/CUMT-Alethic-Insight-Lab/recruitment-exam-kit#readme) 导出并清洗指定会话，只上传去除思考过程与工具输出正文的清洗件。招新服务处理已提交的清洗件，不远程读取考生文件。`server/app/cleaned_report.py` 重建评审 Markdown。

- 安装器、构建与清洗测试以[套件 README](https://github.com/CUMT-Alethic-Insight-Lab/recruitment-exam-kit#readme)为准；下载与 SHA256 以 [Releases](https://github.com/CUMT-Alethic-Insight-Lab/recruitment-exam-kit/releases) 为准。
- `server/static/kit-version.json` 只是考试客户端 OTA 兼容元数据，更新必须对应已验证的安装包 URL、版本与 SHA256。
- 不宣称任意两个最新版兼容。联动发布须记录考试服务 commit/tag、套件 commit/tag、安装包版本/SHA256，并用该组合验证登录、题目、清洗交卷、暂存转发及报告下载；LAN/P2P 通路分别验证。

## 文档与相关项目

- [产品职责与公开边界](docs/REPOSITORY_BOUNDARIES.md)、[隔离与分仓历史](docs/migration.md)、[工作区保全清单](docs/WORKSPACE_MIGRATION.md)、[考试流程设计](docs/platform_flow.md)
- [内部成员平台（独立仓）](https://github.com/CUMT-Alethic-Insight-Lab/alethicinsight-member-platform)
- [join-us](https://github.com/CUMT-Alethic-Insight-Lab/join-us)：招新流程与下载入口
- [open-onboarding](https://github.com/CUMT-Alethic-Insight-Lab/open-onboarding)：入组练手与贡献流程

公开 Git 只放代码、通用模板和合成夹具。真实题库归 `question-bank`，考生归档归 `exam-archive`，私有运维交接归 `infra-handoff`，招新物料归 `recruitment-materials`；它们的存在不是读取秘密或迁移真实数据的授权。`Alethic-Insight-Frontend-Templates` 不在本次范围。既有真实成员账号迁出须单独审批；本次不读秘密、不清除旧数据、不部署生产。

## License · 许可与归属

CUMT Alethic Insight Lab。页面中的招新素材版权归实验室所有。

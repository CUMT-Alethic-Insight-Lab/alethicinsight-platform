# Recruitment Exam Platform · 招新机试服务端

中国矿业大学 **Alethic Insight** 实验室的招新平台服务端：FastAPI + SQLite + 原生 HTML/JS 管理端。负责报名、账号、问卷、面试评审、题库抽题、交卷暂存转发、服务端报告重建与归档。

This repository owns the recruitment backend and admin console. The candidate exam kit is maintained separately in [recruitment-exam-kit](https://github.com/CUMT-Alethic-Insight-Lab/recruitment-exam-kit).

## 职责与仓库边界

| 位置 | 职责与权威来源 |
| --- | --- |
| `server/` | 平台 API、数据库迁移、管理页面及服务端测试；运行行为以本仓实现和测试为准 |
| `server/app/cleaned_report.py` | 将已上传的 `cleaned.jsonl` 重建为供评审下载的 Markdown |
| `server/deploy/` | 服务端部署脚本和模板；真实环境参数只在私有运维记录中维护 |
| `docs/` | 流程及历史方案；设计草案不代表已实现或已部署的功能 |
| [recruitment-exam-kit](https://github.com/CUMT-Alethic-Insight-Lab/recruitment-exam-kit) | 考生端启动器、本地机试服务、会话清洗、LAN 接收机及安装器的唯一源码权威；不再位于本仓 `exam_kit/` |
| [infra/interface/alethicinsight-cli](https://github.com/CUMT-Alethic-Insight-Lab/recruitment-exam-platform/tree/main/infra/interface/alethicinsight-cli) | 公共 CLI 接口归属本平台的 infra 接口项目；本次移除 PR 不引入接口实现，不另拆 MCP 仓库 |

接口目录由独立迁移维护，本 PR 的基线 `c97b980` 尚未包含 `infra/`；上述链接指向平台主线的目标归属，不是本分支内已经落地的文件。`docs/agent-interface/` 保留为接口设计资料，不能替代实现与契约测试。

本仓不维护考生端安装包构建，也不接管官网独立仓或前端模板仓。

## For Candidates · 会话隐私与审查

考生在自己的电脑上使用 AI 工具作答，由**独立考试套件**导出并清洗指定会话，只上传清洗件（去除思考过程与工具输出正文）。考生端如何读取会话、过滤事件和打包上传，以 [exam-kit 源码与 README](https://github.com/CUMT-Alethic-Insight-Lab/recruitment-exam-kit#readme) 为准，清洗测试也在该仓运行。本仓只处理已提交的清洗件，不提供远程读取考生电脑文件的功能。

## 本地构建与测试

服务端没有额外前端编译步骤。建议使用隔离的 Python 环境：

```bash
python -m venv .venv
# 激活 .venv 后，在仓库根目录执行
python -m pip install -r server/requirements.txt
cd server
python -m pytest tests -q
```

页面 JavaScript 的回归测试需要 Node.js；没有 Node.js 时相关用例会跳过，完整验证应安装 Node.js 后运行全量测试。测试使用合成夹具与测试数据库，不需要生产凭据或成员数据。

考试套件的构建、测试和安装器发布命令请在 [exam-kit README](https://github.com/CUMT-Alethic-Insight-Lab/recruitment-exam-kit#readme) 查看；不要在本仓执行旧的 `cd exam_kit` 命令。

## 下载与发布

- 考生端源码、安装器构建和发布说明：[recruitment-exam-kit](https://github.com/CUMT-Alethic-Insight-Lab/recruitment-exam-kit)。
- 版本发布记录：[exam-kit Releases](https://github.com/CUMT-Alethic-Insight-Lab/recruitment-exam-kit/releases)。以该仓发布说明提供的下载地址、版本和 SHA256 为准，不把历史安装包链接或旧哈希当作最新版本。
- 平台侧的 `server/static/kit-version.json` 是现有客户端 OTA 消费的兼容元数据，不是套件源码或构建入口；更新它必须与套件已验证的发布版本、URL 和 SHA256 配套。
- 服务端发布和回滚：[server/deploy/README.md](server/deploy/README.md)。本次分仓不执行部署、不改生产参数。

## 服务端与 exam-kit 的版本兼容

分仓只改变源码位置，不改变 API、鉴权、上传字段或数据结构，也不要求旧客户端立即升级。继续保留 `/api/auth/*`、`/api/campaigns/{cid}/auth/*`、考试与交卷相关兼容端点；公共 CLI 的新接口不能代替旧客户端协议。

目前没有跨仓自动维护的版本兼容矩阵，不能宣称任意两个最新版都兼容。每次联动发布需记录**平台 commit/tag + exam-kit commit/tag + 安装包版本/SHA256**，并完成以下检查：

1. 本仓全量服务端测试通过（包含旧客户端登录、题目下发、上传、暂存转发与报告重建回归）。
2. exam-kit 仓全量测试与安装器构建/校验通过。
3. 在隔离环境以该版本套件验证登录、开考/换题、清洗交卷与评审报告下载；启用 LAN/P2P 的场景分别验证对应通路。
4. 对齐 `cleaned.jsonl` 事件格式、附件大小限制、清洗规则与服务端 `cleaned_report.py`；有破坏性变更时先提供兼容窗口，再升级客户端和发布元数据。

## 分仓迁移与回滚

- 从平台 `origin/main` 的 `c97b980` 创建独立移除分支；只删除该版本中 Git 跟踪的 `exam_kit/`，不删除旧本地目录、不搬走未提交文件，也不改写既有历史。
- 新开发者分别克隆平台与 [exam-kit](https://github.com/CUMT-Alethic-Insight-Lab/recruitment-exam-kit)，不要继续把套件代码提交回平台。
- `push-server.sh` 只打包服务端；`push-lab.sh` 仍部署服务端和 LAN 接收机，但必须用 `EXAM_KIT_DIR` 显式指定经过兼容验证的独立套件检出目录，详见部署说明。缺少接收机源码时应在联网操作前失败。
- 本 PR 不迁移数据库、安装包对象、私有运行配置或归档数据，不更改运行中服务。
- 源码回滚：通过新 PR revert 本次移除提交（不 reset/clean 旧工作区）；独立套件仓和既有本地文件仍保留。运行版本回滚：按部署说明恢复上一服务端 release，接收机单独恢复之前记录的套件版本；需要时同步恢复匹配的 OTA 元数据，不能盲目降级数据库。

## 架构

```text
考生电脑（独立 recruitment-exam-kit）
  ├─ exam_server.py      本地机试服务（127.0.0.1:8899）
  └─ cleaner.py          指定 AI 会话导出与清洗
       │ HTTPS 上传 / P2P / LAN 接收机（独立套件的 session_receiver.py）
       ▼
云端 VPS（本仓 server，ROLE=edge）
  ├─ 报名 / 账号 / 问卷 / 面试评审 / 题库抽题
  └─ multipart 暂存 → 定时转发 lab 收口
       ▼
实验室小主机（server，ROLE=authoritative）
  └─ 权威库 + ingest-staged 收口 + 即时归档
```

## 私有数据与权威来源

公开 Git 只放代码、通用模板和合成测试数据。不要提交或读取用于迁移的真实凭据、成员/考生资料、会话、数据库、附件和归档；私有仓的存在不等于授权本次迁移访问它们。

| 私有仓 | 内容 |
| --- | --- |
| `question-bank` | 真实机试题库与解析校验；本仓 `server/tests/fixtures/` 仅为合成夹具 |
| `infra-handoff` | 真实主机地址、账号、密钥路径与运维记录；公开部署说明仅为模板 |
| `exam-archive` | 考生清洗件、仓库链接与附件 |

本地 `data/`、运行时配置、密钥、测试输出及未提交内容不作为分仓提交来源。服务端行为以本仓代码/测试为准，客户端以独立套件仓为准，发布产物以对应发布记录和哈希为准。

## 相关仓库

- [join-us](https://github.com/CUMT-Alethic-Insight-Lab/join-us)：招新流程、准备建议与下载入口。
- [open-onboarding](https://github.com/CUMT-Alethic-Insight-Lab/open-onboarding)：入组后的练手任务与贡献流程。

## License · 许可与归属

CUMT Alethic Insight Lab。页面中的招新素材版权归实验室所有。

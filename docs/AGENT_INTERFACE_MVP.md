# 内部成员平台 MVP：本地运行与人工运维手册

本手册服务于独立的内部成员产品，不再把它作为招新平台增量。第一阶段同仓布局为 `member-platform/server/` 与 `member-platform/infra/interface/alethicinsight-cli/`；根 `server/` 仅考试。共同基线 `229e69c` 尚为共享 DB/账号/启动的混合实现，隔离代码须经集成测试和 PR 审查，本次文档不冒称已解耦。旧设计与测试原记录见 [migration.md](migration.md)。

- [产品安装入口](../member-platform/README.md)、[infra 安装入口](../member-platform/infra/README.md)
- [API 与工作流](agent-interface/docs/04-api-and-workflows.md)、[OpenAPI](agent-interface/contracts/openapi-skeleton.yaml)
- [验收](agent-interface/docs/09-roadmap-and-acceptance.md)、[决策](agent-interface/docs/10-decision-register.md)、[集成交接](agent-interface/docs/11-agent-handoff.md)

## 1. 服务、数据与权限边界

成员服务根示例为 **`http://localhost:8902`**，内部 REST `/api/v1`，网页 `/org`；CLI base 是服务根，不含 `/api/v1`。不预设成员生产域名、`/recruitment` 前缀或考试 edge/authoritative 反代链路，不把根考试部署脚本用作成员部署。

成员服务拥有独立 DB、账号、网页 Bearer session 与 CLI grant；不能使用考试 DB、账号凭据或会话。相同 API 登录路径或配置键拼写不代表身份共用。只有本成员库当前 member/admin 可用组织接口；网页管理还需当前 admin，CLI scope 不授予 review。考试管理员不是成员平台管理员。

API 名保持不变；`Application` 仍是项目加入等组织事务，不是招新 application。根考试保留 `/api/auth/*`、`/api/campaigns/*` 和旧 exam-kit 协议，但不对成员库提供桥接。CLI 一次性 code 交换是短时授权，不是 OAuth/OIDC。本次不交付 Gitea、远程 MCP、官网内置模型或真实 Agent 兼容认证。

## 2. 隔离本地运行

从仓库根在新的 Git Bash/Linux 终端执行，要求成员代码已集成；目标文件缺失时停止，不退回根 `server` 启动组织接口。配置变量须在导入 `app.config` 前设置。

```sh
python -m venv .venv-member
# Windows Git Bash；Linux 使用 source .venv-member/bin/activate
source .venv-member/Scripts/activate
python -m pip install -r member-platform/server/requirements.txt
export ALE_THIC_DATA_DIR="$PWD/.local-member"
export ALE_THIC_DB_PATH="$ALE_THIC_DATA_DIR/member.db"
export ALE_THIC_ROLE=authoritative
export PUBLIC_PREFIX=''
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
python -m uvicorn app.main:app --app-dir member-platform/server --host 127.0.0.1 --port 8902
```

沿用配置键名不等于继承考试配置。只允许新建开发目录，不指向 `server/data`、考试 `.local-exam`、生产镜像或备份。临时密钥不落盘、不打印、不上线；初始化管理员与密码变更遵循成员应用提示，仅创建合成账号，不复制真实成员。提交前检查状态，禁止提交 DB/WAL、凭据、日志。

另一个终端访问 `http://localhost:8902/org` 与 `http://localhost:8902/openapi.json`。隔离应用负责注册 org router、最小成员网页登录与成员表初始化，不加载考试报名、交卷、staging、归档或批次回收。`/org` 禁止 iframe 嵌套，组织错误保持 envelope/request_id。成员服务即使保留 `ALE_THIC_ROLE` 兼容配置，也不能借此挂载考试 edge 功能；生产拓扑另审。

同时运行考试服务的命令见[根 README](../README.md)。双服务的 DB 路径、虚拟环境、数据目录和配置值必须不同；不能以两个端口共用同一库假装独立。

## 3. CLI 安装与登录

Python 3.10+，在成员虚拟环境从仓库根安装同一发行包，提供两个正式入口：

```sh
python -m pip install ./member-platform/infra/interface/alethicinsight-cli
# 每次演练新建仓库外隔离目录，不读取或复制任何历史凭据
export ALETHICINSIGHT_CONFIG_DIR="$(python -c 'from pathlib import Path; import tempfile; root = Path.cwd().resolve(); base = Path(tempfile.gettempdir()).resolve(); assert base != root and root not in base.parents; print(tempfile.mkdtemp(prefix="alethicinsight-member-", dir=base))')"
test -n "$ALETHICINSIGHT_CONFIG_DIR" || exit 1
export ALETHICINSIGHT_API_BASE_URL=http://localhost:8902
alethicinsight-cli --help
alethicinsight-cli auth login
alethicinsight-cli auth status --json
alethicinsight-cli projects list --recruiting --limit 20 --json
alethicinsight-cli knowledge search '成员' --json
alethicinsight-cli forms schema project-join --json
alethicinsight-cli applications list --mine --limit 20 --json
```

新配置使用 `ALETHICINSIGHT_API_BASE_URL` 与 `ALETHICINSIGHT_CONFIG_DIR`；旧 `ALETHIC_API_BASE_URL`、`ALETHIC_BASE_URL`、`ALETHIC_CONFIG_DIR` 仅兼容。显式服务根不能省略，不依赖旧考试 URL 默认值。`/api/v1/auth/cli/*` 路由不因移动包目录更名。

CLI 随机 request_id，引导可信成员 `/org?cli_request=...`。用户核对 scopes 后取一次性 code，在 CLI 隐藏提示输入；密码、网页 token、code、CLI token 和确认 token 不进 Agent 上下文。默认只读，草稿需明确授权：

```sh
alethicinsight-cli auth login --scope profile:read:self --scope applications:create --scope applications:read:self --scope projects:read
```

先读 schema，再准备本地脱敏 `application.json`，project_id/revision 以实际返回为准：

```json
{"kind":"project-join","form_revision":"1","fields":{"project_id":"LOCAL_TEST_PROJECT_ID","motivation":"希望参与本地测试项目并验证加入流程","weekly_hours":4,"notes":"仅本地演练"}}
```

```sh
alethicinsight-cli applications submit --file application.json --dry-run --json
alethicinsight-cli applications draft --file application.json --json
```

`--dry-run` 只 validate；draft 持久化未提交草稿。CLI `applications submit` 也只准备草稿并返回需网页确认（退出码 7），没有 `--confirm`、最终提交或 review。用户必须在可信 `/org?draft_id=...` 重新核对，网页取得一次性 confirmation 后提交 `draft_id + confirmation`，不是再传 fields 或旧嵌套 confirmation_token。

分页只取一页，后续用 `--cursor`，页大小 1..50。`auth logout` 尝试 `DELETE /auth/cli/grants/self` 自撤销并清除本地凭据，只有确认响应才可认定服务端撤销；网络失败时到可信网页撤销或等过期。不能将凭据目录放仓库、共享目录或备份中。

## 4. 本地 stdio MCP 入口

同包安装后已有 MCP，不安装第二发行包。Host 使用刚才授权的同一成员服务根与隔离目录；以下路径需由操作者本地填写，JSON 不展开 shell 变量：

```json
{
  "mcpServers": {
    "alethicinsight": {
      "command": "/absolute/path/to/member-venv/bin/alethicinsight-mcp",
      "args": ["--cli", "/absolute/path/to/member-venv/bin/alethicinsight-cli"],
      "env": {
        "ALETHICINSIGHT_API_BASE_URL": "http://localhost:8902",
        "ALETHICINSIGHT_CONFIG_DIR": "/absolute/path/to/the-new-isolated-directory-from-section-3"
      }
    }
  }
}
```

Windows 使用 `Scripts/alethicinsight-mcp.exe` / `Scripts/alethicinsight-cli.exe`。不要在 env 写 token，不复用默认或历史凭据目录，不把 shell 字符串/非可信程序交给 `--cli`。本地 stdio stdout 专供协议，不启动远程 HTTP MCP。工具只允许发现、读取与准备草稿，不包括确认签发、最终提交、review、SQL、shell 或任意 URL 抓取。

协议自动测试不等于真实 Host 接入。支持版本以集成后包实现、`--help` 和真实握手为准；具体 Host/版本与结果分别记录。参见 [CLI/MCP](agent-interface/docs/05-cli-mcp-skills.md)。

## 5. 受控知识同步

同步仅处理人工审核的本地公开 checkout，不在 HTTP 请求内爬取，不读取私有仓或生产资料。脚本归成员 `member-platform/server/scripts/sync_org_knowledge.py`；若隔离集成未完成，不运行根旧脚本来绕过。沿用原同步的 `governance-public` allowlist、UTF-8 `.md/.txt`、路径/数量/体积限制，拒绝 restricted、隐藏文件和路径逃逸。

保持第 2 节同一成员 DB 环境，在空开发库完成初始化后：

```sh
python member-platform/server/scripts/sync_org_knowledge.py --help
python member-platform/server/scripts/sync_org_knowledge.py --local-dir /path/to/reviewed/governance-public --revision FULL_40_HEX_COMMIT
# 覆盖名单须另行人工审查，再加 --allowlist /path/to/approved-manifest.json
```

```json
{"source_repo":"governance-public","documents":[{"path":"docs/zh-CN/membership.md","title":"成员制度","access_level":"public"}]}
```

来源路径、许可、完整 commit 和 checkout 状态由操作者核实；脚本 revision 格式校验不证明 remote/commit 一致。同步按来源清单 upsert 并删除未列出的旧索引，**空清单会清空该来源**；先备份明确的本地成员库，审阅清单，失败不可部分写入。完成后用成员 CLI 验证来源、版本、可见性；撤除文档不能留下旧摘要。这不是全仓镜像或真实知识导入已完成的声明。

## 6. 测试与验收记录

从仓库根分别在对应环境执行：

```sh
(cd server && python -m pytest tests -q)
(cd member-platform/server && python -m pytest tests -q)
python -m pip wheel --no-deps ./member-platform/infra/interface/alethicinsight-cli --wheel-dir /path/to/new-temporary-wheel-dir
```

本页先给命令，不编造通过数；当前文档工作未运行应用测试。集成交接须记录 commit、系统/依赖、实际命令、退出状态、失败和跳过。验证还包括：

- 考试进程不挂载 `/org` 或组织 `/api/v1`；成员进程不挂载考试业务或运行考试维护任务。
- 双空库、合成账号同时启动，账号与 session/grant 不跨产品生效，管理员权限不继承；任何一套初始化/维护不改变另一套 DB。
- 成员真实 HTTP + 实际 CLI/MCP 子进程闭环、撤权/草稿确认/幂等与权限负例；干净 wheel 安装和两个入口。
- YAML 解析、内部 `$ref`、operationId/路径参数、本地 Markdown 链接检查，成员 `/openapi.json` 与人工契约对照。

原 451/566/311 等历史数字移至 [migration.md](migration.md)，不当作隔离后的验收。真实浏览器、两种真实 Agent Host、独立 POSIX 主机、目标硬件、离机备份/恢复、TLS/反代和生产发布各自待验，不能用协议测试代替。

## 7. 备份与隔离恢复（未执行的人工方案）

成员备份集合仅含本产品 DB、必要文件、知识来源清单/revision 与受保护配置；考试 DB、考生清洗件/附件/归档另按考试策略备份，不把混合旧库直接复制为成员库。SQLite 使用 backup API/`.backup` 得到一致副本，活跃写入时不得遗漏 WAL；跨文件一致性需要经批准停写窗口。

备份加密、限制访问、离机保留，记录代码/schema、摘要、时间、RPO/RTO 与责任人，不提交 Git、不备份 CLI 明文凭据。恢复到新隔离目录，不覆盖原件，核验 integrity_check、成员权限和事务闭环；不得连到考试库。恢复快照可能复活会话、grant、code 与 confirmation，重新开放前必须按审查过的流程使旧凭据失效并要求重新登录。

真实混合库中的成员身份如何迁出、哪些历史记录可迁、密码与授权如何失效，均须另立数据迁移方案，当前未执行。不提供生产覆盖/DELETE 命令。

## 8. 发布前与回滚（未执行）

先审查同仓隔离 PR 与合成数据验收，再设计成员独立部署、私有网络/域名、TLS、反代、配置/秘密管理、审计与备份。不重跑旧考试部署脚本，不把考试 edge 当成员写入权威，也不以本次文档授权 nginx reload。

源码回退走新的 revert PR；不 reset/clean 或覆盖原脏工作区。运行回退需记录旧成员 release、schema 兼容与一致快照，先停新写入和授权；不能为了代码回退 DROP 表或覆盖考试 DB。不兼容迁移需另审维护窗口、故障态备份、数据损失/补录策略与恢复后凭据撤销。真实数据迁移与生产发布都是独立审批事项，本次未执行。

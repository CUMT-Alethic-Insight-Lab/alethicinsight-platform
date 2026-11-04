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
export MEMBER_PLATFORM_DATA_DIR="$PWD/.local-member"
export MEMBER_PLATFORM_DB_PATH="$MEMBER_PLATFORM_DATA_DIR/member.db"
export MEMBER_PLATFORM_ROLE=authoritative
export MEMBER_PLATFORM_PUBLIC_PREFIX=''
# 仅首次初始化生成：在受控秘密管理位置保留，重启必须恢复同一值
export MEMBER_PLATFORM_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
(cd member-platform/server && python scripts/bootstrap_member.py --student-id local-owner)
```

bootstrap 交互读取两次唯一临时管理员密码（不少于 12 字符），只允许空成员库执行，不通过参数/文件传密码。没有默认管理员、默认密码或自助注册。初始化成功后，同一终端执行：

```sh
(cd member-platform/server && python -m uvicorn app.main:app --host 127.0.0.1 --port 8902)
```

成员配置只读取 `MEMBER_PLATFORM_*`；旧 `ALE_THIC_*`、`SECRET_KEY` 不作为配置来源。独立成员密钥必须不少于 32 字符且不同于考试密钥，**首次生成后必须保留，重启恢复同一值**以及相同 DATA_DIR/DB_PATH，再只执行 uvicorn。不重新生成密钥、不重做 bootstrap；更换密钥会使已有密码验证失败。密钥存受控秘密管理位置，不打印、提交、粘贴给 Agent。PowerShell 与全部配置见 [成员服务 README](../member-platform/server/README.md)。

只允许新建开发目录，不指向 `server/data`、考试 `.local-exam`、生产镜像或备份，不复制真实成员。成员应用工作目录为 `member-platform/server`，不设置指向根考试应用的 `PYTHONPATH`。提交前检查状态，禁止提交 DB/WAL、凭据、日志。

先访问 `http://localhost:8902/login`，以显式 bootstrap 的 `local-owner` 和临时密码登录，**必须先改密**才能查询组织 API/管理成员；再进入 `/org`。`/openapi.json` 是运行时契约。隔离应用不加载考试报名、交卷、staging、归档或批次回收；`/org` 禁止 iframe 嵌套，组织错误保持 envelope/request_id。成员实例角色用 `MEMBER_PLATFORM_ROLE`，不是 `ALE_THIC_ROLE`；生产拓扑另审。

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
alethicinsight-cli applications list --mine --limit 20 --json
```

新配置使用 `ALETHICINSIGHT_API_BASE_URL` 与 `ALETHICINSIGHT_CONFIG_DIR`；旧 `ALETHIC_API_BASE_URL`、`ALETHIC_BASE_URL`、`ALETHIC_CONFIG_DIR` 仅兼容。显式服务根不能省略，不依赖旧考试 URL 默认值。`/api/v1/auth/cli/*` 路由不因移动包目录更名。

CLI 随机 request_id，引导可信成员 `/org?cli_request=...`。用户核对 scopes 后取一次性 code，在 CLI 隐藏提示输入；密码、网页 token、code、CLI token 和确认 token 不进 Agent 上下文。默认授权只读，**读取 forms schema 与校验/草稿一样，需要 `applications:create`**，不是只读登录后的可用命令。本人准备申请时先重新明确授权，完成网页同意与 CLI 交换后再查 schema，不放宽服务端权限：

```sh
alethicinsight-cli auth login --scope profile:read:self --scope applications:create --scope applications:read:self --scope projects:read
alethicinsight-cli forms schema project-join --json
```

新的 login scope 列表不会与旧 grant 自动合并；仍需知识查询时显式加 `--scope knowledge:read`。读到当前 schema 后，再准备本地脱敏 `application.json`，project_id/revision 以实际返回为准：

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

本页先给命令，不编造通过数；本次教程复核未运行两套全量 pytest，实际启动/HTTP/CLI 结果见下方。集成交接须记录 commit、系统/依赖、实际命令、退出状态、失败和跳过。完整验收还包括：

- 考试进程不挂载 `/org` 或组织 `/api/v1`；成员进程不挂载考试业务或运行考试维护任务。
- 双空库、合成账号同时启动，账号与 session/grant 不跨产品生效，管理员权限不继承；任何一套初始化/维护不改变另一套 DB。
- 成员真实 HTTP + 实际 CLI/MCP 子进程闭环、撤权/草稿确认/幂等与权限负例；干净 wheel 安装和两个入口。
- YAML 解析、内部 `$ref`、operationId/路径参数、本地 Markdown 链接检查，成员 `/openapi.json` 与人工契约对照。

### 2026-11-04 集成教程复核

Windows / Python 3.14，在仓库外创建新的成员 venv 与合成成员库，执行 `python -m pip install -r member-platform/server/requirements.txt`；CLI 从当前源码的临时副本安装，避免在源码树留下构建产物，两个已安装入口 `--help` 均退出 0。成员进程使用本手册 `MEMBER_PLATFORM_*`，工作目录为成员 server，执行 `python -m uvicorn app.main:app --host 127.0.0.1 --port 8902`（验证时另加 `--no-access-log`）。结果：

- 执行未修改的 `scripts/bootstrap_member.py --student-id local-owner` 原入口，合成密码输入两次，初始化成功。工具终端没有 Windows 交互控制台，原生 getpass 管道探针超时；本次以 runpy 执行原脚本 main、包装 stdin 触发标准库非控制台输入，不算交互隐藏输入验收，教程仍要求用户在真实终端交互输入。
- 真实 HTTP `/login`、`/org`、`/openapi.json` 返回 200；bootstrap 管理员登录后未改密查询 `/api/v1/me` 为 403，改密后为 200；创建合成成员、成员登录/强制改密与项目查询成功。
- 停止再以同一 DB/成员密钥启动，管理员和成员的新密码仍能登录，成员查询成功。密钥仅在本次临时演练进程内保留，未读取或写入生产秘密。
- 已安装 CLI 显式指向 `http://localhost:8902` 与新私有临时配置目录：非交互 login 退出 3、授权 URL 指向 8902；通过真实 HTTP 自动化成员授权码/交换接口，用包自带 CredentialStore 保存合成 grant，而不是在浏览器人工登录。
- 默认只读 grant 的 `auth status`、projects/knowledge/本人 applications 查询退出 0；forms schema 退出 4（权限拒绝）。显式授予 `applications:create` 后 forms schema 退出 0；logout 确认 `server_revoked: true`。未放宽权限。
- 考试另建 venv，安装 `server/requirements.txt`，使用另一空开发库与独立密钥启动 8901；不跟随重定向的 `GET /` 返回 200，`HEAD /` 返回 405，故[部署验证](../server/deploy/README.md)必须使用 GET，不能用 `curl -I` 声称 200。首次额外考试探针因误用只含成员依赖的环境缺 captcha 失败，改用完整独立考试环境后通过，不修改应用代码。

本次验证进程全部停止，临时环境/DB/凭据已删除。未运行全量 pytest、真实浏览器点击或真实 Agent Host，也未执行生产部署、真实账号/知识迁移；HTTP 自动化不是人工网页确认验收。

原 451/566/311 等历史数字移至 [migration.md](migration.md)，不当作隔离后的验收。真实浏览器、两种真实 Agent Host、独立 POSIX 主机、目标硬件、离机备份/恢复、TLS/反代和生产发布各自待验，不能用协议测试代替。

## 7. 备份与隔离恢复（未执行的人工方案）

成员备份集合仅含本产品 DB、必要文件、知识来源清单/revision 与受保护配置；考试 DB、考生清洗件/附件/归档另按考试策略备份，不把混合旧库直接复制为成员库。SQLite 使用 backup API/`.backup` 得到一致副本，活跃写入时不得遗漏 WAL；跨文件一致性需要经批准停写窗口。

备份加密、限制访问、离机保留，记录代码/schema、摘要、时间、RPO/RTO 与责任人，不提交 Git、不备份 CLI 明文凭据。恢复到新隔离目录，不覆盖原件，核验 integrity_check、成员权限和事务闭环；不得连到考试库。恢复快照可能复活会话、grant、code 与 confirmation，重新开放前必须按审查过的流程使旧凭据失效并要求重新登录。

真实混合库中的成员身份如何迁出、哪些历史记录可迁、密码与授权如何失效，均须另立数据迁移方案，当前未执行。不提供生产覆盖/DELETE 命令。

## 8. 发布前与回滚（未执行）

先审查同仓隔离 PR 与合成数据验收，再设计成员独立部署、私有网络/域名、TLS、反代、配置/秘密管理、审计与备份。不重跑旧考试部署脚本，不把考试 edge 当成员写入权威，也不以本次文档授权 nginx reload。

源码回退走新的 revert PR；不 reset/clean 或覆盖原脏工作区。运行回退需记录旧成员 release、schema 兼容与一致快照，先停新写入和授权；不能为了代码回退 DROP 表或覆盖考试 DB。不兼容迁移需另审维护窗口、故障态备份、数据损失/补录策略与恢复后凭据撤销。真实数据迁移与生产发布都是独立审批事项，本次未执行。

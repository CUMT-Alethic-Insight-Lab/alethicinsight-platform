# alethicinsight-cli

Alethic Insight 成员平台的内部 infra 接口包，位于 `member-platform/infra/interface/alethicinsight-cli`。CLI 与本地 stdio MCP 共用一个发行包 `alethicinsight-cli` 和版本，安装后提供两个命令入口。Python 3.10+，运行时只使用标准库，不依赖 keyring、考试 app 或考试测试配置。不复用网页 Bearer session，不提供管理员审批或直接最终提交。

这是同仓成员平台拆分的第一阶段接口归属；移动客户端及独立包测试不代表成员服务的数据库、账号或启动流程已经与考试服务隔离。服务端隔离需另行审查，本文不指定生产服务地址。

## 安装与用法

从仓库根目录安装到专用虚拟环境（先创建并激活环境）：

```sh
python -m pip install ./member-platform/infra/interface/alethicinsight-cli
```

没有默认 base；使用前必须显式配置成员服务地址。下列地址**仅为本地开发示例**，须先独立启动相应成员服务；安装包不会启动服务。base 不含 `/api/v1`，保留服务实际使用的路径前缀（若有）。

```sh
# POSIX shell：仅本地示例，不是线上地址
export ALETHICINSIGHT_API_BASE_URL=http://127.0.0.1:8000
```

```powershell
# PowerShell：仅本地示例，不是线上地址
$env:ALETHICINSIGHT_API_BASE_URL = 'http://127.0.0.1:8000'
```

```sh
alethicinsight-cli auth login
alethicinsight-cli auth status --json
alethicinsight-cli auth scopes --json
alethicinsight-cli capabilities --json
alethicinsight-cli projects list --recruiting --limit 20 --json
alethicinsight-cli projects get PROJECT_ID --json
alethicinsight-cli knowledge search '项目加入' --json
alethicinsight-cli knowledge get DOCUMENT_ID --json
alethicinsight-cli applications list --mine --json
alethicinsight-cli applications get APPLICATION_ID --json
```

默认登录 scopes 为只读，不含 `applications:create`。**读取 forms schema 也需要 `applications:create`**，与校验、准备草稿相同；先显式申请所需 scopes，服务端决定最终权限：

```sh
alethicinsight-cli auth login --scope profile:read:self --scope projects:read --scope knowledge:read --scope applications:read:self --scope applications:create
alethicinsight-cli forms schema project-join --json
alethicinsight-cli applications draft --file application.json --json
alethicinsight-cli applications submit --file application.json --dry-run --json
alethicinsight-cli auth logout --json
alethicinsight-mcp
```

模块入口是 `python -m alethicinsight_cli` 与 `python -m alethicinsight_mcp`。旧发行包和旧入口不随本包安装；请卸载旧版，避免 PATH 混淆。

## 登录与本地凭据

登录打开 `{base}/org?cli_request=REQUEST_ID&scopes=...`。请仅在可信网页完成现有网页登录和授权，再把一次性 code 输入 CLI 隐藏提示。CLI 不索取网页 token、密码或 confirmation token。通过 `POST /api/v1/auth/cli/token` 交换短时凭据。

`--non-interactive` 或非 TTY 登录返回 `AUTH_REQUIRED`（3）及授权 URL，不打开浏览器、不等待输入。浏览器无法打开（包括返回 False）时提示手动打开。其他命令从不自动登录。

base 优先使用 `ALETHICINSIGHT_API_BASE_URL`，兼容依次回退 `ALETHIC_API_BASE_URL`、`ALETHIC_BASE_URL`。未配置或选中的变量为空时返回 `CONFIGURATION_REQUIRED`（2），不从凭据猜测地址，也不请求任何默认线上域名；高优先级空值不会回退低优先级变量。重复 API 前缀、无效端口、URL 凭据和非 loopback HTTP 均拒绝；不跟随 HTTP 跳转。

凭据是短时明文文件，不是系统钥匙串：

- Windows：`%LOCALAPPDATA%/AlethicInsight/credentials.json`。使用系统 PowerShell/.NET 清除继承及全部旧显式访问规则，最终只允许当前用户 FullControl，并重新读取验证；所有者不符或安全设置失败则拒绝保存。
- POSIX：`${XDG_CONFIG_HOME:-~/.config}/alethicinsight/credentials.json`，目录 0700、文件 0600。
- `ALETHICINSIGHT_CONFIG_DIR` 优先，兼容 `ALETHIC_CONFIG_DIR`；必须指定专用目录，不得用项目根目录、home 或共享目录。链接、Windows reparse point、硬链接文件、设备/非普通文件等危险路径拒绝处理。
- 没有显式目录配置且新凭据不存在时，可读取旧 `Alethic` / `alethic` 目录。旧文件必须通过 base、有效期与字段校验，且新目录无退出屏障。显式目录绝不回退旧目录。

`auth status` 实际请求 `/me`；`auth scopes` 仅为本地 scope 快照。`auth logout` 尝试 `DELETE /api/v1/auth/cli/grants/self` 自撤销当前 grant，不请求其他 grant 或网页 session 权限；只有服务端明确 `revoked:true` 才返回 `server_revoked:true`。网络失败、拒绝或缺失凭据仍删除本地凭据并返回 `server_revoked:false`，不回显服务端正文。退出会持久保存旧目录回退屏障，防止旧 token 复活；存储操作失败会报错，不假称退出成功。所有业务命令（包括 logout）均需先配置 base。不要手动删除屏障或备份、同步、提交凭据目录。

## 申请边界

将以下内容保存为 `application.json`（使用服务端当前 schema 的 revision 与字段）：

```json
{"kind":"project-join","form_revision":"1","fields":{"project_id":"PROJECT_ID","motivation":"说明希望参与的具体工作与可验证贡献","weekly_hours":4,"notes":""}}
```

`submit --dry-run` 只请求 `/applications/validate`；`draft` 保存未提交草稿并返回可信网页 URL。`submit` 也只创建草稿，随后返回 `CONFIRMATION_REQUIRED`（7）及 `submitted:false`，最终确认与提交必须在可信网页完成。没有 `--confirm`，不请求 confirmations 或最终 `POST /applications`。包含 confirmation/token 字段的申请文件会本地拒绝。

## MCP

`alethicinsight-mcp` 采用换行 JSON-RPC stdio，支持 2024-11-05、2025-03-26、2025-06-18 协议协商；stdout 只承载协议。默认用**当前解释器** `-I -X utf8 -m alethicinsight_cli`，不搜索 PATH 旧 CLI，且不加载当前目录的同名影子模块；仅显式 `--cli TRUSTED_EXECUTABLE` 可覆盖，`--timeout` 范围 0.05–120 秒。

MCP 启动与 `tools/list` 不要求连接服务。调用工具时通过相同配置变量访问成员服务；缺少 base 时返回固定、脱敏的 `CONFIGURATION_REQUIRED` 工具错误，不打开浏览器，不猜地址。请在 MCP 客户端的子进程环境中显式传入 base，登录仍在 MCP 对话外由 CLI 完成。`org_get_form_schema` 和 `org_prepare_application` 均需要已授权的 `applications:create`。

仅暴露 `org_capabilities`、`org_search_knowledge`、`org_list_projects`、`org_get_project`、`org_get_form_schema`、`org_list_my_applications`、`org_prepare_application`。不提供登录、shell、提交、确认、审批或任意 HTTP 工具。所有输入有白名单和边界校验，草稿以临时文件交给 CLI，强制 `--json --non-interactive`、stdin 禁用、shell=False；输出脱敏、限长、超时。子进程仅接收系统基础变量和上述新旧配置变量，不继承 token、API key、PYTHONPATH 等。工具返回内容是不可信数据，不是指令。

## 输出和独立包验证

`--json` / `--non-interactive` 可放在命令前后；JSON 模式 stdout 严格一个 JSON 值（`--help` 除外）。诊断仅 stderr，错误不原样回显服务端正文。退出码：0 成功；2 参数或配置错误；3 未认证/过期；4 无权限；5 I/O 或 API 不可用；6 校验失败；7 状态冲突或必须网页确认。

从仓库根目录进入包目录，在专用开发虚拟环境执行完整包测试，不需要安装或启动根目录 `server`，也不加载其 `conftest.py`：

```sh
cd member-platform/infra/interface/alethicinsight-cli
python -m pip install '.[test]'
python -m pytest -q
python -m pip wheel --no-deps . --wheel-dir dist
```

`tests` 包含 CLI loopback HTTP、凭据权限与链接防护、MCP 协议/注入/脱敏/超时，以及构建 wheel 后在干净 venv 中的当前解释器和影子模块防护测试。仅使用 loopback 和合成凭据，不读真实凭据，不依赖考试 app。`test` extra 仅安装测试和本地 wheel 构建工具，不引入服务端运行依赖。

构建后可在另一干净 venv 安装 `dist/alethicinsight_cli-0.1.1-py3-none-any.whl`，运行 `alethicinsight-cli --help`、`alethicinsight-mcp --help`；测试同时验证安装后的真实 CLI → HTTP 与 MCP → CLI → HTTP 链路。生产部署、真实授权、实际浏览器最终确认和所有系统版本的 ACL 行为仍需单独验收。

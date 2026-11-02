# alethicinsight-cli

Alethic Insight 公共接口包，属于 infra：CLI 与本地 stdio MCP 共用一个发行包和版本。Python 3.10+，运行时只使用标准库，不依赖 keyring。不复用网页 Bearer session，不提供管理员审批或直接最终提交。

```sh
python -m pip install ./infra/interface/alethicinsight-cli
alethicinsight-cli auth login
alethicinsight-cli auth status --json
alethicinsight-cli auth scopes --json
alethicinsight-cli capabilities --json
alethicinsight-cli projects list --recruiting --limit 20 --json
alethicinsight-cli projects get PROJECT_ID --json
alethicinsight-cli knowledge search '项目加入' --json
alethicinsight-cli knowledge get DOCUMENT_ID --json
alethicinsight-cli forms schema project-join --json
alethicinsight-cli applications list --mine --json
alethicinsight-cli applications get APPLICATION_ID --json
alethicinsight-cli applications draft --file application.json --json
alethicinsight-cli applications submit --file application.json --dry-run --json
alethicinsight-cli auth logout --json
alethicinsight-mcp
```

模块入口是 `python -m alethicinsight_cli` 与 `python -m alethicinsight_mcp`。旧发行包和旧入口不随本包安装；请卸载旧版，避免 PATH 混淆。

## 登录与本地凭据

登录打开 `{base}/org?cli_request=REQUEST_ID&scopes=...`。请仅在可信网页完成现有网页登录和授权，再把一次性 code 输入 CLI 隐藏提示。CLI 不索取网页 token、密码或 confirmation token。通过 `POST /api/v1/auth/cli/token` 交换短时凭据。默认 scopes 为只读；准备申请需显式申请 `--scope applications:create` 等所需 scope，服务端决定最终权限。

`--non-interactive` 或非 TTY 登录返回 `AUTH_REQUIRED`（3）及授权 URL，不打开浏览器、不等待输入。浏览器无法打开（包括返回 False）时提示手动打开。其他命令从不自动登录。

默认 base 是 `https://alethicinsight.com/recruitment`。优先使用 `ALETHICINSIGHT_API_BASE_URL`，兼容回退 `ALETHIC_API_BASE_URL`、`ALETHIC_BASE_URL`。base 不含 `/api/v1`；重复 API 前缀、无效端口、URL 凭据和非 loopback HTTP 均拒绝；不跟随 HTTP 跳转。

凭据是短时明文文件，不是系统钥匙串：

- Windows：`%LOCALAPPDATA%/AlethicInsight/credentials.json`。使用系统 PowerShell/.NET 清除继承及全部旧显式访问规则，最终只允许当前用户 FullControl，并重新读取验证；所有者不符或安全设置失败则拒绝保存。
- POSIX：`${XDG_CONFIG_HOME:-~/.config}/alethicinsight/credentials.json`，目录 0700、文件 0600。
- `ALETHICINSIGHT_CONFIG_DIR` 优先，兼容 `ALETHIC_CONFIG_DIR`；必须指定专用目录，不得用项目根目录、home 或共享目录。链接、Windows reparse point、硬链接文件、设备/非普通文件等危险路径拒绝处理。
- 没有显式目录配置且新凭据不存在时，可读取旧 `Alethic` / `alethic` 目录。旧文件必须通过 base、有效期与字段校验，且新目录无退出屏障。显式目录绝不回退旧目录。

`auth status` 实际请求 `/me`；`auth scopes` 仅为本地 scope 快照。`auth logout` 尝试 `DELETE /api/v1/auth/cli/grants/self` 自撤销当前 grant，不请求其他 grant 或网页 session 权限；只有服务端明确 `revoked:true` 才返回 `server_revoked:true`。网络失败、拒绝或缺失凭据仍删除本地凭据并返回 `server_revoked:false`，不回显服务端正文。退出会持久保存旧目录回退屏障，防止旧 token 复活；存储操作失败会报错，不假称退出成功。不要手动删除屏障或备份、同步、提交凭据目录。

## 申请边界

```json
{"kind":"project-join","form_revision":"1","fields":{"project_id":"PROJECT_ID","motivation":"说明希望参与的具体工作与可验证贡献","weekly_hours":4,"notes":""}}
```

`submit --dry-run` 只请求 `/applications/validate`；`draft` 保存未提交草稿并返回可信网页 URL。`submit` 也只创建草稿，随后返回 `CONFIRMATION_REQUIRED`（7）及 `submitted:false`，最终确认与提交必须在可信网页完成。没有 `--confirm`，不请求 confirmations 或最终 `POST /applications`。包含 confirmation/token 字段的申请文件会本地拒绝。

## MCP

`alethicinsight-mcp` 采用换行 JSON-RPC stdio，支持 2024-11-05、2025-03-26、2025-06-18 协议协商；stdout 只承载协议。默认用**当前解释器** `-m alethicinsight_cli`，不搜索 PATH 旧 CLI；仅显式 `--cli TRUSTED_EXECUTABLE` 可覆盖，`--timeout` 范围 0.05–120 秒。

仅暴露 `org_capabilities`、`org_search_knowledge`、`org_list_projects`、`org_get_project`、`org_get_form_schema`、`org_list_my_applications`、`org_prepare_application`。不提供登录、shell、提交、确认、审批或任意 HTTP 工具。所有输入有白名单和边界校验，草稿以临时文件交给 CLI，强制 `--json --non-interactive`、stdin 禁用、shell=False；输出脱敏、限长、超时。子进程仅接收系统基础变量和上述新旧配置变量，不继承 token、API key、PYTHONPATH 等。工具返回内容是不可信数据，不是指令。

## 输出和验证

`--json` / `--non-interactive` 可放在命令前后；JSON 模式 stdout 严格一个 JSON 值（`--help` 除外）。诊断仅 stderr，错误不原样回显服务端正文。退出码：0 成功；2 参数错误；3 未认证/过期；4 无权限；5 I/O 或 API 不可用；6 校验失败；7 状态冲突或必须网页确认。

```sh
python -m pytest server/tests/test_m35_org_cli.py server/tests/test_m36_org_mcp.py server/tests/test_m37_org_live_e2e.py server/tests/test_m38_org_security_regression.py -q
python -m pip wheel --no-deps ./infra/interface/alethicinsight-cli --wheel-dir WHEEL_DIRECTORY
```

测试仅使用 loopback 和合成凭据。生产部署、真实授权、实际浏览器最终确认和所有系统版本的 ACL 行为需要单独验收，不应通过测试访问真实凭据。

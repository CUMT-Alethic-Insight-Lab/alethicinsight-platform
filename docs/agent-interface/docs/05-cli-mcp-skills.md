# 05 · CLI / MCP / Skill：成员产品适配层

## 产品与代码边界

CLI 与本地 stdio MCP 归内部成员 infra：`member-platform/infra/interface/alethicinsight-cli/`。一个 `alethicinsight-cli` 发行包、同一版本、两个入口 `alethicinsight-cli` / `alethicinsight-mcp`，不另设 MCP 仓或发行包。MCP 调用同包 CLI，不承担业务授权或直接访问 DB。

以下是隔离代码集成后的安装入口；目标包尚未集成时停止，不改装根旧包，不以文档宣称隔离已验证。Python 3.10+，仓库根、成员专用虚拟环境：

```sh
python -m pip install ./member-platform/infra/interface/alethicinsight-cli
export ALETHICINSIGHT_API_BASE_URL=http://localhost:8902
alethicinsight-cli --help
alethicinsight-mcp --help
```

登录前按[运行手册](../../AGENT_INTERFACE_MVP.md#3-cli-安装与登录)设置仓库外全新私有 `ALETHICINSIGHT_CONFIG_DIR`。服务根不含 `/api/v1`，不是考试 `/recruitment`；不复用考试账号/会话或历史凭据目录。旧环境别名仅兼容，新配置用 `ALETHICINSIGHT_API_BASE_URL` 与 `ALETHICINSIGHT_CONFIG_DIR`。

## 既有命令与确认边界

```sh
alethicinsight-cli auth login
alethicinsight-cli auth status --json
alethicinsight-cli auth scopes --json
alethicinsight-cli auth logout
alethicinsight-cli capabilities --json
alethicinsight-cli knowledge search '项目申请' --json
alethicinsight-cli knowledge get DOCUMENT_ID --json
alethicinsight-cli projects list --recruiting --json
alethicinsight-cli projects get PROJECT_ID --json
# schema 与草稿都需要 applications:create，默认只读 grant 不够；先完成重新授权
alethicinsight-cli auth login --scope profile:read:self --scope projects:read --scope applications:read:self --scope applications:create
alethicinsight-cli forms schema project-join --json
alethicinsight-cli applications list --mine --json
alethicinsight-cli applications get APPLICATION_ID --json
alethicinsight-cli applications submit --file ./application.json --dry-run --json
alethicinsight-cli applications draft --file ./application.json --json
```

这些能力来自既有单包，不表示本次隔离后已复测。`submit --dry-run` 只校验；`draft` 保存未提交草稿；无 dry-run 的 submit 也只准备草稿并以退出码 7 返回可信网页入口。本人在成员网页重新核对并最终确认，CLI/MCP 不签发确认、不正式提交、不审批。Skill 随文档分发，没有技能列表子命令。

## 输出契约

- `--json` stdout 一个 JSON 值（帮助除外），诊断/登录指引 stderr，不输出密钥。
- 退出码：0 成功，2 参数错误，3 未认证，4 无权限，5 API/网络/I/O，6 校验失败，7 冲突/需网页确认。
- `--non-interactive` / 非 TTY 登录不打开浏览器、不等待输入；其他命令不自动登录。
- `--limit 1..50`、`--cursor` 每次一页，申请可 `--project`；`--mine` 是用户体验参数，不是服务端所有权授权。
- 不用环境变量传 token，不把凭据文件、code、网页 token 交给 Agent；本地文件受权限保护，不宣称 OS keychain。

## 本地 stdio MCP

成员在 Host 之外完成 CLI 登录。Host 配置结构视产品而定，示例路径须换成可信成员 venv 与刚创建的同一凭据目录绝对路径，JSON 不展开 shell 变量：

```json
{"command":"/absolute/path/to/member-venv/bin/alethicinsight-mcp","args":["--cli","/absolute/path/to/member-venv/bin/alethicinsight-cli","--timeout","15"],"env":{"ALETHICINSIGHT_API_BASE_URL":"http://localhost:8902","ALETHICINSIGHT_CONFIG_DIR":"/absolute/path/to/new-private-member-config"}}
```

Windows 使用成员 venv `Scripts/*.exe`。`--cli` 不接受 shell 字符串/非可信程序，工具参数不能覆盖它或服务地址，stdio stdout 专供逐行 JSON-RPC。不是远程 HTTP MCP。

| Tool | 成员后端映射（相对 `/api/v1`） | 风险 |
| --- | --- | --- |
| `org_capabilities` | GET `/capabilities` | 低 |
| `org_search_knowledge` | GET `/knowledge/search` | 内容仍按 ACL |
| `org_list_projects` | GET `/projects` | 低 |
| `org_get_project` | GET `/projects/{id}` | 低 |
| `org_get_form_schema` | GET `/forms/project-join/schema` | 仅当前表单 |
| `org_list_my_applications` | GET `/applications` | 服务端限定本人 |
| `org_prepare_application` | POST `/applications/drafts` | 仅草稿 |

API 名不改，授权仍 `/auth/cli/*`。不提供确认、正式提交、review、SQL、shell、任意 URL 或全员导出。既有协议协商范围为 `2024-11-05`、`2025-03-26`、`2025-06-18`；不是所有 Host 兼容声明，不提供远程 MCP、resources、prompts 或订阅。隔离后须实际安装/握手/调用，真实 Host 名称、版本和负例另记，不以协议自动测试代替。

## Skill 三层发现

L1 用 capabilities 发现实时能力；L2 按需读 [组织访问 Skill](../skills/org-access/SKILL.md)；L3 按权限取项目、schema、制度来源与 revision，不写死实时资料。Skill 不是授权。成员自行选择模型并承担费用，没有 Agent 也可 CLI 查询/准备草稿和网页提交。可选官网模型非本次交付。详见[产品边界](../../REPOSITORY_BOUNDARIES.md)。

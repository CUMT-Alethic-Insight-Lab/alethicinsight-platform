# 05 · CLI / MCP / Skill：Agent 友好的适配层

## 产品与代码边界

CLI 与 MCP 同属 infra 的公共接口，位于 `infra/interface/alethicinsight-cli/`，单仓、单发行包、单版本。发行名为 `alethicinsight-cli`，提供 `alethicinsight-cli` 与 `alethicinsight-mcp` 两个入口；不另设 MCP 仓，不保留两个顶层产品目录。MCP 是调用 CLI 的本地协议适配器，不承担业务授权或直接访问数据库。

从仓库根安装一次即可获得两个入口（Python 3.10+）：

```sh
python -m pip install ./infra/interface/alethicinsight-cli
alethicinsight-cli --help
alethicinsight-mcp --help
```

## 已实现命令与确认边界

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
alethicinsight-cli forms schema project-join --json
alethicinsight-cli applications list --mine --json
alethicinsight-cli applications get APPLICATION_ID --json
alethicinsight-cli applications submit --file ./application.json --dry-run --json
alethicinsight-cli applications draft --file ./application.json --json
```

`submit --dry-run` 只进行服务端校验；`draft` 保存待确认草稿。无 dry-run 的 `applications submit` 也只创建草稿并以退出码 7 返回可信网页确认入口，不能完成正式提交。用户必须在可信网页重新核对内容并确认；CLI/MCP 不签发确认、不提交、不审批。不提供技能列表子命令，Skill 是随文档分发的说明。

## CLI 输出契约

- `--json` 时 stdout 为一个 JSON 值（帮助输出除外）；日志与登录指引写 stderr，不输出密钥。
- 退出码：0 成功；2 参数错误；3 未认证；4 无权限；5 API/网络不可用；6 校验失败；7 冲突或要求网页确认。
- `--non-interactive` 或非 TTY 登录不打开浏览器、不等待输入；其他命令不自动登录。
- 分页使用 `--limit 1..50`、`--cursor`，申请列表可用 `--project`；每次只读取一页。
- 服务根通过 `ALETHICINSIGHT_API_BASE_URL` 设置，不含 `/api/v1`；专用凭据目录通过 `ALETHICINSIGHT_CONFIG_DIR` 设置。旧 `ALETHIC_API_BASE_URL`、`ALETHIC_BASE_URL`、`ALETHIC_CONFIG_DIR` 仅为兼容别名，新配置不要使用。
- 不通过环境变量传 token；不把本地凭据文件、一次性 code 或网页 token 交给 Agent。

## 本地 stdio MCP

成员在 MCP 会话外完成 CLI 登录后，由 Host 启动同一发行包的入口：

```json
{"command":"alethicinsight-mcp","args":["--cli","alethicinsight-cli","--timeout","15"],"env":{"ALETHICINSIGHT_API_BASE_URL":"http://127.0.0.1:8901"}}
```

生产配置应指定可信本地可执行文件的绝对路径，Windows 使用 venv 的 `Scripts/alethicinsight-mcp.exe` 和 `Scripts/alethicinsight-cli.exe`。`--cli` 不是 shell 字符串；工具参数不能覆盖它或服务地址。

| MCP Tool | 后端映射 | 风险 |
|---|---|---|
| `org_capabilities` | GET `/capabilities` | 低 |
| `org_search_knowledge` | GET `/knowledge/search` | 低，内容仍受 ACL |
| `org_list_projects` | GET `/projects` | 低 |
| `org_get_project` | GET `/projects/{id}` | 低 |
| `org_get_form_schema` | GET `/forms/{kind}/schema` | 低 |
| `org_list_my_applications` | GET `/applications?mine=true` | 中，个人信息 |
| `org_prepare_application` | POST `/applications/drafts` | 中，仅草稿 |

API 表中路径相对 `/api/v1`；`/auth/cli/*` 授权路由不因发行名变化而改名。不提供最终提交、确认签发、review、SQL、shell、任意 URL 抓取或全员列表工具。stdout 仅承载逐行 JSON-RPC，日志不混入协议。

实现协商范围为 `2024-11-05`、`2025-03-26`、`2025-06-18`，不代表所有客户端完整规范兼容。只提供本地 stdio，不提供远程 MCP、资源、prompts 或订阅。真实 Host 名称、版本、握手与工具调用结果需要另行实测，不以协议自动测试代替。

## Skill 三层发现

- **L1**：薄入口说明，通过 `alethicinsight-cli capabilities --json` 发现实时能力。
- **L2**：按需读取 [组织访问 Skill](../skills/org-access/SKILL.md)，说明工作流、权限与输入输出。
- **L3**：按用户权限检索项目、表单与带来源/版本的文档；不把实时数据写死在 Skill。

Skill 不是授权规则。成员自行选择模型并承担个人模型费用；没有 Agent 也可通过 CLI 查询和准备草稿，再由网页最终提交。可选官网模型并非本次交付。详见[仓库边界](../../REPOSITORY_BOUNDARIES.md)。

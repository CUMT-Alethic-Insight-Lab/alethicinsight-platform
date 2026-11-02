# CLI / Agent 使用示例

以下命令对应本地 MVP；先按 [MVP 手册](../../AGENT_INTERFACE_MVP.md)安装单包、设置隔离服务根并完成授权。示例不代表已部署生产或已验证任意真实 Agent Host。

## 场景一：成员自己查询

```sh
alethicinsight-cli auth login
alethicinsight-cli auth status --json
alethicinsight-cli projects list --recruiting --json
alethicinsight-cli knowledge search "项目申请" --json
```

CLI 不输出隐私令牌；真实文档有 `source_url` 与更新时间。

## 场景二：个人 Agent 辅助填表

用户：“我要申请加入一个视觉方向项目，先帮我看看有哪些在招人。”

Agent：调用 `alethicinsight-cli projects list --recruiting --json`，展示已授权结果并请用户选择。

用户：“我选第一个，你帮我填表。”

Agent：调用 `alethicinsight-cli forms schema project-join --json`，按 schema 从用户消息中提取字段；只询问尚缺信息。展示草稿和声明，经用户同意后以 `alethicinsight-cli applications draft --file application.json --json` 准备草稿，再由用户在返回的可信网页核对并最终提交。CLI/MCP 不执行最终提交。

## 场景三：Bash 脚本中使用

```sh
set -eu
alethicinsight-cli projects list --json > projects.json
python3 -m json.tool projects.json >/dev/null
```

如果认证过期，CLI 返回非零退出码和标准化错误，脚本停止；不得自动尝试使用共享管理员 Token。

## 场景四：接入支持 MCP 的个人 Agent

从仓库根安装同一个发行包，成员先在 Host 之外完成授权：

```sh
python -m pip install ./infra/interface/alethicinsight-cli
alethicinsight-cli auth login
```

Host 的本地 stdio 启动配置示意：

```json
{"command":"alethicinsight-mcp","args":["--cli","alethicinsight-cli"],"env":{"ALETHICINSIGHT_API_BASE_URL":"http://127.0.0.1:8901"}}
```

两个入口来自同一包/版本；正式 Host 配置使用可信 venv 绝对路径（Windows 为 `Scripts/*.exe`），不填 token。stdio 上只能传协议消息，日志写 stderr。各 Host 配置格式与真实兼容性应分别实测。旧 `ALETHIC_API_BASE_URL`、`ALETHIC_BASE_URL`、`ALETHIC_CONFIG_DIR` 仅作兼容别名，新配置使用 `ALETHICINSIGHT_API_BASE_URL`、`ALETHICINSIGHT_CONFIG_DIR`。

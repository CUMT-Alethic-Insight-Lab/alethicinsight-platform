# 内部成员平台 infra · CLI / MCP

内部产品的接口基础设施，不是考试套件，也不是私有运维交接仓。源码布局为 `member-platform/infra/interface/alethicinsight-cli/`：一个 `alethicinsight-cli` 发行包、一个版本，安装提供 `alethicinsight-cli` 和本地 stdio `alethicinsight-mcp` 两个入口。MCP 调用同包 CLI，二者只通过成员 REST API 访问业务，不直接读数据库。

## 安装与服务选择

Python 3.10+；从仓库根在成员专用虚拟环境中执行。下面是隔离代码集成后的入口，不应在目标目录缺失时改装根目录旧包：

```sh
python -m pip install ./member-platform/infra/interface/alethicinsight-cli
export ALETHICINSIGHT_API_BASE_URL=http://localhost:8902
alethicinsight-cli --help
alethicinsight-mcp --help
```

服务根不含 `/api/v1`。本地成员服务启动见 [成员平台 README](../README.md)。不把历史考试 `/recruitment` URL 当成员服务默认值；公网成员入口尚未指定。

## 隔离凭据与登录

在登录前新建仓库外私有目录，不读取或复制历史凭据：

```sh
export ALETHICINSIGHT_CONFIG_DIR="$(python -c 'from pathlib import Path; import tempfile; root = Path.cwd().resolve(); base = Path(tempfile.gettempdir()).resolve(); assert base != root and root not in base.parents; print(tempfile.mkdtemp(prefix="alethicinsight-member-", dir=base))')"
test -n "$ALETHICINSIGHT_CONFIG_DIR" || exit 1
alethicinsight-cli auth login
alethicinsight-cli auth status --json
alethicinsight-cli projects list --recruiting --limit 20 --json
alethicinsight-cli knowledge search '成员' --json
```

CLI 引导本人打开成员服务 `/org?cli_request=...`，在可信网页登录并核对 scope，将一次性 code 输入 CLI 隐藏提示。不要向 Agent 交付密码、网页 token、code 或 grant。默认授权只读；草稿需要明确授权 `applications:create`，最终提交及 review 不由 CLI/MCP 执行。`auth logout` 尝试服务端自撤销并清除本地凭据；只有实际响应确认才宣称服务端已撤销。

旧 `ALETHIC_API_BASE_URL`、`ALETHIC_BASE_URL`、`ALETHIC_CONFIG_DIR` 只是兼容别名，新示例使用上述正式变量。Host 必须显式使用相同成员服务根及本次创建的隔离目录；JSON 配置不展开 shell 变量。完整 stdio 配置、草稿流程与限制见 [MVP 手册](../../docs/AGENT_INTERFACE_MVP.md)。

## 验证

```sh
python -m pip wheel --no-deps ./member-platform/infra/interface/alethicinsight-cli --wheel-dir /path/to/new-temporary-wheel-dir
(cd member-platform/server && python -m pytest tests -q)
```

这些是待执行的命令，不是通过声明。还需在干净临时环境安装 wheel、运行两个正式入口，并对隔离成员服务执行真实 CLI/MCP 合成数据闭环。协议测试不代表真实 Agent Host、生产 TLS、跨平台 ACL 或浏览器确认均已验证。本次不发布包、不推送、不部署、不迁移真实成员凭据。

# 内部成员平台

面向 Alethic Insight 内部认证成员的独立产品：知识检索、项目目录、项目加入申请、状态查询和网页审核。网页、REST、CLI 与本地 stdio MCP 共用成员业务契约；招新报名、机试、评审和考生活档不属于本产品。

这是第一阶段同仓隔离入口，源码目标为 `member-platform/server/`，工具位于 `member-platform/infra/`。代码隔离与运行证据须经集成 PR 审查；仅有这份 README 不代表服务已完成集成或部署。历史混合实现与已撤销方案见 [迁移记录](../docs/migration.md)。

## 安装与本地启动

以下命令适用于隔离代码集成后的布局；若 `member-platform/server/requirements.txt` 尚不存在，先完成代码集成，不要退回根 `server` 启动组织接口。Python 环境、数据目录与进程独立于考试服务。

从仓库根在新的 Git Bash/Linux 终端运行：

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

这里沿用服务配置键的拼写，不沿用考试配置值。**不得指向考试 DB、数据目录、备份或真实成员资料**；若集成实现调整配置键，必须同步本示例并实际运行验证。密钥仅在当前 shell 使用，不写入仓库。不要并用同一 `app` 的 Python 导入路径启动两套服务，应各用对应终端/虚拟环境和 `--app-dir`。

- 服务根：`http://localhost:8902`；网页：`http://localhost:8902/org`。
- REST：`http://localhost:8902/api/v1`；运行时契约：`http://localhost:8902/openapi.json`。
- 仅使用本地合成账号初始化和演练；初始管理员/密码变更以集成后应用提示为准，不复用考试账号。
- 成员平台不继承考试服务的 edge 暂存转发、`/recruitment` 反代、考试归档与批次回收任务。公网域名、反代、部署和真实账号迁移待另行审查。

## 账号、会话与权限

成员服务维护自己的账号和数据库；相同学号或用户名不表示两个产品共享身份。网页使用本服务不透明 Bearer session；CLI 使用经成员网页授权的一次性 code 换短时、可撤销 grant，不是 OAuth/OIDC。服务端逐请求核验当前 member/admin、scope 和资源 ACL。考试管理员不是成员平台管理员；CLI grant 即使属于本服务管理员也没有 review 权限。

CLI/MCP 只允许读取、校验、准备草稿。本人在可信 `/org` 网页核对内容后才能最终提交，当前网页 admin 才能审核。不得把网页 token、code、CLI token 或确认 token 粘贴给 Agent。跨产品会话、账号、数据与权限隔离必须用自动测试及双服务真实 HTTP 调用证明，不靠路径改名证明。

## CLI 与本地 MCP

参见 [infra 安装说明](infra/README.md)和[完整运行手册](../docs/AGENT_INTERFACE_MVP.md)。CLI/MCP 同一个 `alethicinsight-cli` 发行包和版本，不另建 MCP 仓：

```sh
python -m pip install ./member-platform/infra/interface/alethicinsight-cli
export ALETHICINSIGHT_API_BASE_URL=http://localhost:8902
alethicinsight-cli --help
alethicinsight-mcp --help
```

登录前设置仓库外全新、私有的 `ALETHICINSIGHT_CONFIG_DIR`；不要使用历史默认凭据目录。服务根不含 `/api/v1`，不得依赖旧考试 URL 默认值。

## 开发验证与交付状态

```sh
(cd member-platform/server && python -m pytest tests -q)
```

本页只列标准命令，不预填通过数。本地验收应同时启动考试 8901 与成员 8902，使用两个空库和合成账号，验证跨服务登录态拒绝、考试组织路由不可用、成员流程不加载考试数据与回收任务。CLI/MCP、真实浏览器、真实 Agent Host、目标硬件、备份恢复和生产验收分别记录，不能相互替代。

当前文档工作不执行代码安装、生产部署、账号迁移或真实知识导入。待集成实现与自动验证完成后，仍须单独批准部署与真实数据迁移；后者不是本纠正 PR 的完成条件。详见 [验收门禁](../docs/agent-interface/docs/09-roadmap-and-acceptance.md)和[产品边界](../docs/REPOSITORY_BOUNDARIES.md)。

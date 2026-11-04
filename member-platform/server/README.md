# 内部成员服务（第一阶段隔离）

这是同仓 `member-platform/` 内独立运行的内部产品，不是考试应用的路由别名。工作目录必须为本目录，启动模块为本目录 `app.main:app`；不要在仓库根以原 `server` 的 `PYTHONPATH` 启动它。

## 隔离与安全边界

- 仅有成员账号、网页登录会话/限流/审计、组织 principal/CLI 授权、项目、知识和事务申请表。**没有 campaign/application/question/exam/interview 表，不导入旧考试 app，不启动 purge/archive/staging 或其他考试生命周期。** `/api/v1/applications` 是组织事务申请，不是考试报名表。
- 所有服务配置只读取 `MEMBER_PLATFORM_` 前缀。`SECRET_KEY`、`ALE_THIC_DB_PATH` 等旧变量不作为配置来源；仅用来检测误共用。缺少独立密钥、密钥短于 32 字符、与当前进程显式设置的考试 `SECRET_KEY` 相同，均拒绝使用。
- 默认数据库为本目录 `data/members.db`。每次连接检查 SQLite `application_id=0x4D454D42` 及表白名单；初始化仅可采用全新空库或已标记成员库。含任意考试表/未知表、非成员标记或已有但未标记的 account 库都会**在写入前拒绝**。拒绝指向已知考试数据目录或 `ALE_THIC_DB_PATH`。不要手动给旧库加标记，不要复制真实账号、会话、生产数据或考试密钥。
- 不存在默认管理员、学号密码、自助注册或自动迁移。管理员首次初始化必须显式 bootstrap；新增/重置成员密码为每次新生成的随机临时密码，强制改密后才能调用组织 API/管理接口。
- 账号角色为 `member/admin/inactive`。为现有接口兼容接受 `applicant` 作为**不可登录、无组织权限的停用角色**，不会创建报名信息或提供考试能力。
- 浏览器只使用 `member_platform_session_v1`，不读取考试 localStorage 键。推荐本地不同端口、部署不同 origin，严禁共用反向代理身份或考试数据库。Bearer 会话/CLI token 仅存 SHA-256；密码为随机盐 PBKDF2-SHA256（100,000 次）后以独立服务密钥做 HMAC 存储。兼容客户端散列协议意味着服务端不能证明原密码长度，浏览器要求 12+ 字符且服务端拒绝常见弱密码；必须通过 HTTPS（本地可 localhost）传输，客户端散列也应视为敏感凭据。
- 网页/CLI 授权仍分离：CLI 只获显式短时 scope，不能使用网页管理接口、签发正式申请确认或代替人工提交。原页面的授权同意、草稿/规范化预览、内容绑定的一次性确认、幂等重试、审批池及审计语义完整保留。
- 改角色/重置密码删除全部网页登录会话、撤销全部 CLI grant 和未兑换 code；本人改密保留当前网页会话，撤销其他会话、所有 CLI grant 与未兑换 code。退出登录撤销该网页会话；CLI 撤销继续支持 `/api/v1/auth/cli/grants/self`。
- 登录失败按账号及实际连接 IP 持久限流（10 次/10 分钟）；不直接相信任意 `X-Forwarded-For`/CF 头。反代必须限制直连并通过 uvicorn 的受信代理配置提供真实 `request.client`；不要使用 `--forwarded-allow-ips '*'` 对不受信网络开放。CLI 授权另有限流和兑换尝试次数限制。
- 当前没有成员服务自动清理/备份任务；组织申请/审计不会被考试回收误删。备份、保留策略、TLS、凭据托管、部署及真正独立仓映射需单独审查，不在此阶段自动执行。

## 本地启动（PowerShell）

在仓库根执行：

```powershell
cd member-platform/server
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
# 仅首次初始化生成；受控保留此值，重启时恢复原值，不重新生成
$env:MEMBER_PLATFORM_SECRET_KEY = (& .venv/Scripts/python -c "import secrets; print(secrets.token_urlsafe(48))")
$env:MEMBER_PLATFORM_DATA_DIR = "$PWD/data"
$env:MEMBER_PLATFORM_DB_PATH = "$PWD/data/members.db"
.venv/Scripts/python scripts/bootstrap_member.py --student-id local-owner
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8902
```

bootstrap 会交互读取两次临时管理员密码（不少于 12 字符，不通过命令行或文件传递）。只允许空库执行，不能用于覆盖或重置已有账号。**必须保留首次生成的独立服务密钥**供后续重启使用；更换密钥将导致已有密码验证失败，不应每次重启重新生成。示例不创建任何默认身份，也不会输出密码或密钥到服务日志。

访问 `http://localhost:8902/login`：以显式配置的管理员账号和临时密码登录，修改初始密码后进入成员管理创建成员，或访问 `/org` 使用项目、知识、申请和 CLI 授权。管理员可在 `/login` 查看成员、修改角色或重置密码；随机临时密码仅在响应和当前页面短暂展示，页面 60 秒后隐藏，不写 localStorage/日志。请通过可信私密渠道交付本人。

## 配置

| 变量 | 默认 / 作用 |
| --- | --- |
| `MEMBER_PLATFORM_SECRET_KEY` | 无默认，必须是与考试服务不同的 32+ 字符密钥 |
| `MEMBER_PLATFORM_DATA_DIR` | 本目录 `data` |
| `MEMBER_PLATFORM_DB_PATH` | `DATA_DIR/members.db`，只允许独立成员库 |
| `MEMBER_PLATFORM_PUBLIC_PREFIX` | 空；受信反代剥离的路径前缀，例如 `/members` |
| `MEMBER_PLATFORM_SESSION_DAYS` | 1（范围 1–30） |
| `MEMBER_PLATFORM_ROLE` | `authoritative`；`edge` 拒绝组织及成员管理写入，不自动同步数据 |
| `MEMBER_PLATFORM_ORG_CLI_TOKEN_SECONDS` | 900（范围 60–3600） |
| `MEMBER_PLATFORM_ORG_CLI_CODE_SECONDS` | 300（范围 30–600） |

## 知识同步

仅从已准备好的本地、获批公开/成员文档克隆读取，不访问网络，不导入考试资料：

```powershell
.venv/Scripts/python scripts/sync_org_knowledge.py --local-dir C:/work/governance-public --revision <完整40位commit>
```

数据库须先经 bootstrap 或服务启动初始化。可用 `--allowlist approved-documents.json` 指定严格白名单；默认仅含治理仓三个制度文档。保留原有路径逃逸、隐藏文件、可见性、大小及幂等同步检查。

## 测试

在仓库根、包含集成后的内部 CLI/MCP 包时，标准命令：

```powershell
python -m pytest member-platform/server/tests -q
```

测试包含适配的 m31–34、m37–39（不复制 m35 CLI/凭据权限或 m36 MCP 单测）、新增成员登录管理/数据库隔离/生命周期边界，以及真实独立 uvicorn + CLI + MCP 申请闭环。Node.js 用于已有组织页面 DOM 合约测试。所有测试只使用临时合成数据。

本服务工作树尚未集成新 CLI 包时，显式指定原 infra 源验证，不写入或修改 CLI 文件：

```powershell
$env:MEMBER_PLATFORM_TEST_CLI_SOURCE = "$PWD/infra/interface/alethicinsight-cli"
python -m pytest member-platform/server/tests -q
Remove-Item Env:MEMBER_PLATFORM_TEST_CLI_SOURCE
```

默认 CLI 测试路径始终为 `member-platform/infra/interface/alethicinsight-cli`，缺包会失败而非静默跳过。集成树必须取消此临时覆盖再运行标准命令。

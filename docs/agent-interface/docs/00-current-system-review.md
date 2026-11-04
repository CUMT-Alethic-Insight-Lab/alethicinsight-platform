# 00 · 现有系统核实与方案评审

## 当前结论：撤销旧增量方案

2026-11-04 修订：内部成员平台与招新筛选是独立产品。旧“把招新平台逐步扩展为成员事务平台、复用身份与数据库”结论已撤销，不再作为实施依据。第一阶段同仓 `member-platform/` 独立成员 server 与 infra，根 `server/` 仅考试；不是最终分仓，不改历史误命名远端，不迁移真实账号或部署生产。

共同基线 `origin/main = 229e69c` 中，根 `server/app/main.py` 同时挂载考试与组织路由/`/org`，`server/app/db.py` 同一初始化创建账号、考试/组织表，组织鉴权依赖相同账号与网页 session；CLI grant 虽独立于网页 token，仍共用账号、DB 与启动流程。因此**现状不是两个已解耦产品**。必须代码拆离、双空库/进程/合成账号和跨产品凭据拒绝测试，不能只改 README 声称完成。

当前边界、历史与验证门禁见 [产品职责](../../REPOSITORY_BOUNDARIES.md)、[迁移记录](../../migration.md)、[验收](09-roadmap-and-acceptance.md)。下列历史审查不授权继续共库。

## 2026-10-27 历史审查事实

原范围为 `recruitment-exam-platform` main `d3eaf37`、组织公开仓库清单与制度。未读取生产 DB、密钥或私有运维正文，未做线上写入/入侵式验证；本地未提交成员资料不能当作 main 能力，源码不能证明生产已部署同版。

| 当时事实 | 当时证据 | 当前解释 |
| --- | --- | --- |
| FastAPI/Pydantic/SQLite | 根 `server/app/main.py`、`db.py`、`requirements.txt` | 技术可沿用，不沿用考试账号/DB |
| 统一 `/api/auth/login`、`/me`，不是 OAuth/OIDC | 根 `server/app/routes/auth.py` | 网页登录不是 CLI 委托；成员服务需自己的最小登录 |
| 网页不透明 Bearer，服务端 SHA-256 哈希 | 根 `server/app/auth.py`、`static/login.html` | 不是 Session Cookie；成员可复用机制，不复用考试 token |
| 默认 7 天 token、localStorage | 根 `server/app/config.py`、`static/js/topbar.js` | 历史默认不是未来生产安全参数，仍需 XSS/生命周期治理 |
| admin/member/applicant 与管理门禁 | 根 `server/app/constants.py`、`routes/accounts.py` | 相同角色名不代表跨产品权限，也不代替 scope/项目 ACL |
| 招新 application、评审、面试预约已有语义 | 根 `server/app/db.py`、`routes/booking.py` | 成员事务不得读取或混用招新个人评审资料 |
| 批次数据回收与账号生命周期不同 | 根 `server/app/maintenance.py` | 成员独立保留策略，不运行考试回收/归档任务 |
| 静态官网、云 edge、lab authoritative 混合部署 | 根考试部署说明与旧 README | 不是全部都在一台 N5095；更不是成员部署既成事实 |
| 官网源在独立 `website` | 当时公开仓清单与 README | 不重写官网、不假定 Pages 已覆盖成员 API |
| 正式制度来源 `governance-public` | 当时公开 membership/AI 政策 | Skill/示例不能创造成员制度 |
| Gitea、硬件实测、真实设备/项目流程无证据 | 当时未核实 | UNKNOWN，不声称已安装或有库存 |

## 历史身份问题与必须保留的修复

`d3eaf37` 的 `require_admin_session()` 只检查 session kind/pw_changed，`set_role()` 不撤销旧 session，存在降级后旧管理员会话保权缺口。原 PR 修复为角色变化撤销全部会话、管理门禁重新检查当前 `account.role`，并以 `test_role_change_revokes_sessions_and_rechecks_current_role` 覆盖降级及遗留会话。此为历史实现事实，不是本次重新运行测试的声明。

两套产品都须保留当前角色/账号检查与撤权，成员资格/项目 ACL/CLI grant 同样逐请求生效，不能因已修管理员角色便认为所有边界完成。降级、退出、禁用、重置密码、项目撤权及 grant 撤销需要各自回归。

网页 session 不能变成 Agent 凭据；原网页 token 无客户端 scope/audience 等委托语义。成员 CLI 使用一次性 code 交换短时、只读默认、可撤销 grant，不继承 admin review。localStorage/XSS 风险仍需安全渲染、CSP、编码与审计，不靠“不是 Cookie”忽略。

## 仍有效的契约与安全约束

1. `/api/v1` 成员 API 名不变，但只挂载独立成员进程；旧考试 `/api/auth/*`、`/api/campaigns/*` 兼容留在考试进程，不能破坏 exam-kit。
2. 成员 Application 是项目加入事务，不是招新报名；招新问卷/成绩/评语/联系方式默认 restricted，不进通用知识/CLI/MCP。
3. `profile:read:self` 只最小身份，不默认输出学号、手机号、出生年月、政治面貌等；主体响应用稳定不可枚举 ID。
4. 表单带来源/revision/更新时间，申请绑定规范化摘要；变更内容/版本要重新确认。服务端不能从 CLI `--confirm` 判断人类在场，最终确认在可信成员网页。
5. 成员错误 envelope/request_id、验证/429/Retry-After 与分页需契约回归，不声称旧考试 `{detail: ...}` 全部已迁移。
6. 幂等按 principal + operation + 请求摘要隔离，同键异请求冲突，处理确认消费和合法重放，防止重试重复申请。
7. 搜索摘要/原文/缓存/导出同 ACL；CLI 输出可能转交外部模型，restricted 不靠 prompt 保密。
8. 外部同步有界/超时，不在事务请求中阻塞网络；知识从经审核公开制度起步，不索引私聊或全量私有代码。

## 未验证与后续

本次未验证生产版本、真实成员角色变更、域名/TLS、硬件、备份恢复、Gitea、任何真实 Agent Host/外部模型价格或真实审批流程。先完成独立成员无模型查询/草稿/网页闭环及双服务隔离，再另审生产拓扑、RPO/RTO、正式成员维护与真实数据迁移。OAuth/OIDC、Gitea、远程 MCP、官网模型后置。本页是代码/设计审查，不是安全验收完成证明或生产授权。

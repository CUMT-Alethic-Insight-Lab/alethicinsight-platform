# 11 · 第一阶段产品隔离 Coding Agent 交接

## 阅读与范围

先读 [产品边界](../../REPOSITORY_BOUNDARIES.md)、[历史/撤销方案](../../migration.md)、[04 · API](04-api-and-workflows.md)、[09 · 验收](09-roadmap-and-acceptance.md)、[10 · 决策](10-decision-register.md)、[成员运行手册](../../AGENT_INTERFACE_MVP.md)。

不再执行“在根招新 server 注册新增组织路由、复用账号和 DB”的旧交接。内部成员与招新筛选是独立产品，第一阶段同仓隔离 `member-platform/server/` 与 `member-platform/infra/interface/alethicinsight-cli/`，根 `server/` 只做考试。基线 `229e69c` 实际共库/账号/启动，必须代码拆离验证，不能仅文档声称解耦。不是最终分仓，不改历史误命名远端，不编造成员仓 URL。

## 集成检查清单

1. 从根考试启动移除 org router、`/org`、组织业务初始化和耦合任务；保留考试 `/api/auth/*`、`/api/campaigns/*`、招新/机试/评审与独立 exam-kit 兼容。不能以分离成员为由破坏考试账号/管理流程。
2. 在 `member-platform/server` 建立独立依赖/应用/DB/最小登录与成员网页，注册 org router；不导入根考试 app，不运行报名、上传、staging、转发、归档与批次回收。同名 `app` 模块分别在独立进程/导入路径使用。
3. 移动 CLI/MCP 同包到成员 infra，调整打包/测试路径；一个 `alethicinsight-cli` 发行包和版本、两个入口，不拆 MCP 仓。显式服务根 `http://localhost:8902`，不使用考试 `/recruitment` 默认值，不改 `/api/v1` 路由名。
4. 独立配置、数据目录和 DB；成员本库账号/网页 session/CLI grant/权限不查询考试账号，也不复制混合旧库。真实账号、历史数据、部署和远端映射留待后续审批。
5. 成员业务统一 `app.org_auth.require_org_identity(request, scope=None, web_only=False)`；member/admin 加当前 scope/资源 ACL，网页管理还需 web-only + 当前 admin；CLI 不继承 review，考试 admin 不授予成员权限。
6. 保持授权码一次性交换、本人 grant 分页/撤销及当前 grant 自撤销；保持项目/知识/schema/validate/draft/网页确认/幂等提交/本人查询/补件撤回/admin review。提交仅 `draft_id + confirmation`，草稿/校验均不签发确认。
7. 对照成员 `/openapi.json` 核验[人工契约](../contracts/openapi-skeleton.yaml)：字段/状态码、分页、错误、时间与 TTL；静态 drafts/validate 不能被动态 `{id}` 抢占。
8. 受控知识脚本仅在成员独立 DB 操作，人工审核本地来源/版本/许可，摘要与原文同 ACL；不在请求内爬取，不导入真实资料。
9. 用双空库、独立合成账号同时启动考试/成员进程，验证各自初始化/写入/维护不影响另一库，跨产品 session/grant 拒绝；验证根组织路由不可用、成员无考试任务。
10. 分别运行两套标准测试；成员真实 HTTP + CLI/MCP 子进程闭环与负面权限例，wheel 干净安装并检查两个正式入口；运行文档本地链接与契约校验。只记录实际命令/结果，不先写通过数。

## 安全与工作区边界

- 服务端授权不依赖 Skill、prompt、CLI `--confirm` 或“我是管理员”的文本；可信成员网页内容核对后才有一次性确认，变更内容重确认。
- 幂等重放与确认消费在事务内协调；跨用户键不复用结果。不透明 token/code/confirmation 不进源码、URL、日志或模型上下文。
- 招新 restricted 档案/评语/成绩/联系方式不进入成员搜索或 CLI/MCP；不提供 SQL、shell、任意 URL 抓取或全员导出。
- 每个执行者只在分配的干净 worktree 与路径提交；不操作原脏主仓，不 reset/clean，不覆盖不同 HEAD 副本，不触碰 Frontend-Templates。
- 不读秘密、不生产部署、不迁移真实账号，不以合成数据验证代替上述未执行项。

## 完成交接

列出 SHA、变更文件/范围、实际 API/安装/启动命令、测试命令/退出码/结果与失败跳过、代码隔离证明、未执行项及回退方法。代码测试、双服务 HTTP、CLI/MCP 安装、真实浏览器、Windows/POSIX、真实 Agent、硬件、备份恢复、生产与真实迁移分别标注。

第一阶段完成是“同仓隔离代码经 PR 审查与本地合成验证”，不是已分仓/已部署/真实数据已迁。各执行者按授权仅提交自己路径，不自行推送/发布；主代理负责最终跨模块集成与 PR，真实迁移/部署另行审批。

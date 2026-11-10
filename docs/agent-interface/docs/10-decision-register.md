# 10 · 成员产品决策登记与未决事项

> 本页固定产品边界与本地契约，不表示代码隔离已验收或生产已批准。原招新平台增量方案已撤销，历史事实见 [migration.md](../../migration.md)。

## 当前固定决策

| ID | 决策 | 边界与理由 |
| --- | --- | --- |
| D00 | 内部成员平台、招新筛选为独立产品 | 基线 `229e69c` 实际共库/账号/启动，必须代码隔离，不以 README 改名替代 |
| D00-stage1 | 先同仓 `member-platform/server` 与 `member-platform/infra`，根 `server` 仅考试 | 独立 DB/账号/会话/权限/生命周期与进程，不是最终分仓；先 PR 审查再议远端/独立仓映射 |
| D00-remote | 本次不改远端名或新建仓 URL | `alethicinsight-platform` 是历史误改名，不用该名字反推两个产品应共用 |
| D01 | 成员网页沿用不透明 Bearer 机制；CLI 用独立短时 grant | 仅本成员库账号/会话；一次性 `request_id + code`，不是 OAuth/OIDC，考试 token 不可复用 |
| D02 | 成员本库当前 `account.role` member/admin 具有组织权限 | 逐请求核验身份/scope/资源 ACL；考试 admin 不自动有成员权限；网页管理还需当前 admin |
| D03 | 成员 API 内部 `/api/v1`，本地服务根 `http://localhost:8902` | CLI base 不含 `/api/v1`；撤销成员 `/recruitment` 公网前缀预期；不改 API 名，考试兼容 API 留在考试进程 |
| D04 | 现有首个事务为 `project-join` | schema revision + 持久草稿，不宣称资源/设备/通用表单均已实现 |
| D05 | 可信成员网页内容绑定确认与当前 admin 审核 | draft/validate 不返回确认 token；CLI 无最终提交/review；业务审批权仍需组织授权 |
| D07 | 仅索引批准公开/成员低敏来源 | restricted 招新档案、成绩/评语、联系方式、私有代码排除；摘要与原文同 ACL |
| D09 | 沿用 FastAPI/Pydantic/SQLite/vanilla JS 技术栈，不沿用考试 DB | 原“不新增身份库/模块化增量扩展招新”的决定撤销；成员独立运行，不要求微服务化 |
| D12 | CLI/MCP 同包同版本归成员 infra，本地 stdio MCP | 不新建 MCP 仓；无远程传输、OAuth 或真实 Host 认证声明 |
| D13 | 提交 `draft_id + confirmation` 与幂等头 | 主体+操作+请求摘要绑定幂等，确认/提交原子处理，不接受 fields 直提 |
| D14 | 列表统一 `{items,next_cursor}` | 项目、知识、申请/grant 有界分页，不提供全员导出 |

成员代码内身份约定保持 `from app.org_auth import OrgIdentity, require_org_identity`、`require_org_identity(request, scope=None, web_only=False)`；内部 `student_id/role/principal_id/auth_type/scopes` 不授权对外暴露学号。这里 `app` 是独立成员应用，不能导入根考试 `app`。

## 待负责人确认或验证

| ID | 待办 | 不得假定 | 阻塞范围 |
| --- | --- | --- | --- |
| D00-proof | 双服务隔离、标准全量回归与合成 CLI/MCP 闭环 | 文档、同名模块复制或两个端口不等于独立运行 | 第一阶段 PR 验收 |
| D00-repo | 最终独立仓与远端映射 | 不先更名或编造 URL，不因同仓便共用部署 | 后续仓库调整 |
| D00-data | 真实身份、历史事务的最小化映射与迁移方案 | 空库演练不等于真实账号迁移；不复制混合库/旧 token | 另行数据迁移 |
| D02-ops | 正式成员维护、退出与权限负责人 | 本地 role 不替代组织制度，考试角色不继承 | 真实成员运营 |
| D03-ops | 成员独立生产网络、域名、TLS/反代、写入权威 | 考试 edge 暂存/回源不能复用为成员部署 | 生产发布 |
| D05-ops | 正式加入条件和审批责任人 | 开发示例不是制度；技术 admin 不等于业务授权 | 真实项目开放 |
| D06 | Gitea 状态、逐仓权威源与许可 | 未核实，知识同步不是全仓镜像 | 仓库集成 |
| D07-ops | 外部模型可见目录与来源许可 | 成员可见不等于允许外发，提示词不是授权 | 真实知识导入 |
| D08 | Windows/POSIX、浏览器、两种真实 Agent 版本与实测 | 协议/自动测试不能代替实机 | 客户端验收 |
| D10 | 本产品离机备份、密钥/恢复责任、RPO/RTO | 考试归档与同盘副本不等于成员恢复 | 生产上线 |
| D11 | 可选官网模型及预算 | 不影响无模型业务，不承诺人均固定次数 | 可选模型 |
| D12-ops | TTL、日志/审计保留、限流与撤销策略 | 不预填未经实现/实测参数 | 运维安全审核 |

## 更新规则

后续变更记录负责人、日期、依据、受影响 API、兼容/数据与回退策略。独立空库隔离可以先交付审查；生产、真实迁移、远程访问、身份委托和数据公开仍需分别人工批准。参见 [验收](09-roadmap-and-acceptance.md)与[交接](11-agent-handoff.md)。

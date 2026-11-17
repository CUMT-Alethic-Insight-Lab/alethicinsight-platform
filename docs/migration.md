# 产品边界纠正与历史记录

## 2026-11-17：独立成员仓提取与考试仓去重

PR #6 已合并，当前纠正分支从 `origin/main = 9dc7229` 开始。第一阶段同仓隔离已完成，上一阶段交接记录为考试 **308**、成员 **128**、CLI **193**；这些是同仓基线的历史通过数，不是本次独立仓复测结果。

- 成员源码已在本地从原 `member-platform/` 子树保留历史准备独立仓，目标 URL 为 [alethicinsight-member-platform](https://github.com/CUMT-Alethic-Insight-Lab/alethicinsight-member-platform)。发布、公开历史安全审查与独立仓验证由负责人完成，本文不声称远端已发布。
- 本分支移除考试仓跟踪的 `member-platform/` 重复源码。来源仍可追溯至本仓 `9dc7229` 历史及独立成员副本；不读取或删除真实数据。
- 成员详细设计、运行手册、CLI/MCP 示例与 Skill 改为旧 Markdown 路径下的短导航；YAML 契约从考试仓移除，保留契约导航，不再维护两份成员权威。
- 本仓 `server/` 只承担招新/筛选服务端，当前远端名 `alethicinsight-platform` 暂保留，不擅自重命名。CLI/MCP 仍同包同版本，归新成员仓内部 infra，不另建 MCP 仓、不改命令或 API 名。`recruitment-exam-kit` 保持原状。
- 考试兼容协议与部署命令不变，旧成员 API 公网地址 `/recruitment/api/v1`（含子路径）继续默认 **503（fail closed）**，不回源或回落到考试服务。本次不配置成员生产上游，不执行部署或真实账号迁移。

**新成员仓发布与验证完成前，不应合并本拆仓 PR。** 考试仓须运行 `python -m pytest server/tests -q` 和文档链接检查；成员安装、标准测试、单包 CLI/MCP、HTTP 合成闭环及独立路径文档由成员仓另行验收，不能沿用上述同仓数量替代。工作区与历史公开门禁见[保全清单](WORKSPACE_MIGRATION.md)。

## 2026-11-04：撤销招新平台增量扩展方案（历史阶段）

内部成员平台与招新筛选是独立产品。撤销“在现有招新平台上逐步扩展成员事务、共享账号/数据库/启动流程”的实施方案。第一阶段先在同一仓库可审查地隔离：

- 根 `server/` 仅招新筛选，保留考试兼容 API、管理、edge/authoritative、归档与回收职责。
- `member-platform/server/` 独立运行成员产品，拥有独立账号、DB、会话、权限和生命周期。
- CLI 与本地 stdio MCP 同包同版本，归 `member-platform/infra/interface/alethicinsight-cli/`；不拆独立 MCP 仓，不改 API 名。
- 先提交隔离 PR，完成代码审查和双服务合成数据回归，再决定远端名和独立仓映射。这不是最终分仓。

当时暂保留历史误改名 `alethicinsight-platform`，尚未决定成员独立仓 URL。该阶段的“先同仓隔离，再审议独立仓”门禁已由 PR #6 推进；当前分仓目标与发布门禁以上方 2026-11-17 记录为准。`Alethic-Insight-Frontend-Templates` 不在范围内；不修改原脏主仓，不使用 reset/clean，不部署、不读取秘密、不迁移真实账号、DB 或存档。

### 为何不能只改 README

共同基线 `origin/main = 229e69c` 中，根 `server/app/main.py` 注册组织路由与 `/org`；`server/app/db.py` 在同一初始化路径中建立账号、考试与组织表；组织鉴权依赖相同账号与网页会话，CLI grant 虽独立于网页 token，仍依赖同一账号/DB/进程。原 CLI 在根 `infra/interface/alethicinsight-cli/`。因此旧系统**实际尚未解耦**，API 命名空间不是产品隔离。

这些是当时公开源码的历史事实，不是当前 `9dc7229` 的布局，也不是生产数据库或线上版本的核验。当时纠正文档描述的是隔离 PR 必须达到的边界；该阶段已由 PR #6 完成，不能把历史混合实现描述成当前状态。

### 第一阶段完成门禁（历史；PR #6 已合并）

1. 成员代码及 CLI/MCP 移至成员目录；成员服务不导入根考试应用，根考试启动不挂载组织路由/页面或初始化组织业务。
2. 两套标准测试独立运行；两个空库、合成账号、独立端口同时启动，跨产品 token/账号不串用；成员生命周期不执行考试批次回收/归档/上传任务。
3. CLI wheel 干净安装及两个入口工作，显式成员服务根 `http://localhost:8902`，真实 HTTP/CLI/MCP 合成闭环；不依赖考试 `/recruitment`。
4. 文档本地链接、人工 OpenAPI 与成员运行时契约核对；实际命令、结果、失败及跳过原因在集成交接记录，不沿用下列历史通过数。
5. 代码审查接受隔离 PR。生产部署、真实身份迁移、真实知识导入、独立仓/远端调整均另行审批；未执行不写成完成。

当时同仓布局的验证入口（仅作历史记录；当前考试仓不再提供成员路径，勿照抄执行）：

```sh
(cd server && python -m pytest tests -q)
(cd member-platform/server && python -m pytest tests -q)
python -m pip wheel --no-deps ./member-platform/infra/interface/alethicinsight-cli --wheel-dir /path/to/new-temporary-wheel-dir
```

### 后续真实数据迁移与回退（未执行）

独立空库不是既有数据已迁移。需由获授权负责人另审成员来源、字段最小化、账号映射、密码/会话失效、重复身份、审批记录保留、审计和恢复策略。不能直接把混合考试库复制为成员库，不能保留可跨产品复用的 token。生产两套配置、反代、备份与回滚点独立制定，不沿用旧考试 vhost 作为成员入口。

代码回退通过新的 revert PR，保留历史，不 reset/clean 任何旧工作副本。运行/数据回退需另有经批准的维护窗口与一致性备份；不能因源码回退而删除旧表或覆盖数据库。

## 既有历史：保留事实，不再作为实施依据

### 2026-10-27：原组织接口方案与审查

当时审查基线 `d3eaf37`，建议在招新 FastAPI/SQLite 平台中增量扩展组织接口，复用身份和数据库。该方向后来进入 PR #3，组织 API、网页 `/org`、授权码/grant、项目/知识/申请和 CLI/MCP 曾合入平台 main（`d06f26d`）。原角色降级撤权修复、草稿/确认/幂等和成员权限限制是实现事实，不意味着共享产品边界正确。

原运行手册记录（转存，不是本次复测）：

- `cd server && python -m pytest -q`：原记录 **451 passed**。
- 原文记载 `test_m37_org_live_e2e.py` 用真实 uvicorn 与 CLI/MCP 源码子进程、合成账号/项目完成无模型闭环；真实浏览器未验证。
- 当时记录 Windows 两个 wheel 构建成功；这是统一单包前的历史布局，不能当成当前单发行包安装验收。
- 原文曾记录文档 21 个 operation 对照与错误 envelope 核验；不代表当前成员进程契约已复核。

### 2026-11-02：旧布局串行复核记录

原手册记载：20 个文档、44 个本地链接目标存在；diff/JS 语法检查通过；`cd server && python -m pytest -q` 为 **566 passed**，`cd exam_kit && python -m pytest -q` 为 **311 passed**；人工与运行时 OpenAPI 22 个 operation 对齐；单发行 wheel 临时环境安装、两个入口、MCP 隔离模块与 Windows ACL 检查通过。POSIX 权限只有 mock 覆盖。

这些数量只属于原记录的版本、布局与环境，不是本次产品隔离的结果。真实浏览器、真实 Agent Host、独立 POSIX 主机、目标硬件、备份恢复与生产部署当时均未验证。

### exam-kit 已独立的既有事实

早先从平台 `c97b980` 创建考试套件移除分支，后合并 PR #3 后的 main `d06f26d`；平台移除跟踪的 `exam_kit/`，保留了当时根 `infra/` 与组织接口。公共 [recruitment-exam-kit](https://github.com/CUMT-Alethic-Insight-Lab/recruitment-exam-kit) 与私有 [recruitment-materials](https://github.com/CUMT-Alethic-Insight-Lab/recruitment-materials) 已发布；不要恢复平台内旧 `cd exam_kit` 测试入口。本次成员产品纠正不撤销套件独立，也不修改套件仓。

`push-server.sh` 打包考试服务；`push-lab.sh` 还需通过 `EXAM_KIT_DIR` 显式选择已验证的独立套件来源，详情见 [考试部署说明](../server/deploy/README.md)。脚本存在不是部署已执行或本次有部署授权的证据。

现行入口：[根 README](../README.md)、[产品边界](REPOSITORY_BOUNDARIES.md)、[工作区保全清单](WORKSPACE_MIGRATION.md)、[成员运行手册](AGENT_INTERFACE_MVP.md)。

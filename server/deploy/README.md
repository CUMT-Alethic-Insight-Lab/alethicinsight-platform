# 招新平台部署（server/deploy/）

把 `server/` 下的 FastAPI 应用部署到一台 Linux 服务器（Ubuntu 24.04 验证过），
经 nginx 挂在主站 `/recruitment/` 路径下。本文是通用版说明；真实的
主机地址、账号、密钥路径与运维排障记录维护在 org 私有仓 **infra-handoff**。

- 应用入口：`app.main:app`，uvicorn 监听 `127.0.0.1:8901`
- systemd 单元：`alethic-recruitment.service`（User=www-data）
- 站点账号页：`/login`、`/account` 为规范公网入口；nginx 内部 rewrite 至既有
  `/recruitment/login`、`/recruitment/account` 代理链，旧 URL 仍可用，查询参数不变。
- nginx：`/recruitment/` strip 前缀后反代到 8901（片段见 `nginx-recruitment.location.conf`）。
  账号页 API 和资源继续使用 `/recruitment/api/`、`/recruitment/static/`；不要改
  `PUBLIC_PREFIX=/recruitment`，也不要将认证或成员资料 API 改为官网静态路由。
- 发布必须同步云端完整 vhost 的账号页 location 并执行 `nginx -t` 后 reload；
  `push-server.sh` / `push-lab.sh` 仅发布应用，不会自动安装 nginx 配置。
  若使用 Cloudflare Pages/Worker 前置代理，也须放行 `/login`、`/account` 及其尾斜杠版本，
  同时继续回源 `/recruitment/*` 和 `/admin/recruitment`，不能让 Pages 的 SPA fallback 吞掉账号页。
  Pages 配置在官网独立仓，须随官网发布同步核验。
- 考试进程不再提供 `/api/v1`、`/org` 或组织静态资源。`auth/profile/member` 及
  `membership` 仅保留历史考生账号和资料兼容，不是成员产品的账号源或权限服务。
- 成员 API 旧公网地址 `/recruitment/api/v1`（含所有子路径）在两份 nginx 模板中默认
  返回 503（fail closed），不回源考试 lab authoritative，也不回落考试 cloud edge。
  启用旧地址前必须显式配置独立成员产品上游；这是服务端反向代理，**不是 HTTP 重定向**，
  应保留方法、请求体和查询参数，将旧前缀映射到成员进程的 `/api/v1`，独立配置其
  Host/SNI/认证，不得复用考试主库或考试会话。成员产品上游不可用时也不得转到考试进程。
- `nginx-alethicinsight.vhost.conf` 以云端 2026-10-16 存档为基础，现为待审查部署模板，
  含 lab_origin 考试长连接池和热备回落。仓库修改不代表线上已安装；本次隔离没有部署、
  迁移账号或搬运数据库。须先审查隔离 PR，再单独审批成员上游和 nginx 发布。
- 数据目录：`/var/www/recruitment/data`（sqlite，跨 release 持久，属主 www-data）
- venv：`/var/www/recruitment/venv`（跨 release 复用）
- 发布目录：`/var/www/recruitment/releases/<YYYYmmdd-HHMMSS>`，`current` 软链指向当前版

## 一次性初始化（服务器上）

以下命令在服务器上以具备免密 sudo 的部署用户执行。

1. 建目录：

```bash
sudo mkdir -p /var/www/recruitment/releases /var/www/recruitment/data
sudo chown www-data:www-data /var/www/recruitment/data
```

2. 生成环境变量文件 `/etc/alethic-recruitment.env`（含强随机 ADMIN_TOKEN，不要存进任何仓库）：

```bash
TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
printf 'ADMIN_TOKEN=%s\nPUBLIC_PREFIX=/recruitment\nALE_THIC_DATA_DIR=/var/www/recruitment/data\n' "$TOKEN" | \
  sudo tee /etc/alethic-recruitment.env >/dev/null
sudo chmod 600 /etc/alethic-recruitment.env
sudo chown root:root /etc/alethic-recruitment.env
```

3. 安装 systemd 单元：

```bash
sudo cp deploy/alethic-recruitment.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now alethic-recruitment
```

（首次部署前服务会因 current 不存在而启动失败，跑一次下面的日常部署即可；
或先手动跑一次 push-server.sh 再 enable。）

4. nginx：备份并编辑主站站点配置，在 `listen 127.0.0.1:80` 的 server 块内、
   `location /` 之前加入 `nginx-recruitment.location.conf` 中的 location 段，然后：

```bash
sudo nginx -t && sudo systemctl reload nginx
```

## 日常部署（本机）

```bash
DEPLOY_HOST=<user@host> SSH_KEY=<私钥路径> bash server/deploy/push-server.sh
```

`DEPLOY_HOST` / `SSH_KEY` 为必填环境变量（真实取值见私有仓 infra-handoff）。

脚本流程：tar `app static requirements.txt` → ssh 流式上传到家目录中转
（部署用户无权写 /var/www）→ `sudo mv` 到 `/var/www/recruitment/releases/<时间戳>`
并 chown www-data → 建/复用 venv 并 `pip install -r requirements.txt` →
切 `current` 软链 → `systemctl restart alethic-recruitment` → 本机健康检查 →
保留最近 5 个 release。

## 实验室内网小主机（lab，authoritative）

lab 侧部署用 `push-lab.sh`（`LAB_HOST` / `SSH_KEY` 同样走环境变量），
systemd 单元在 `deploy/lab/` 下：主服务、数据回收 timer、以及机试会话
局域网接收机 `alethic-session-receiver.service`（考试机 upload_mode=lan
时接收清洗后的轨迹文档）。

### 分仓后的接收机来源

接收机源码权威为独立公共仓
[recruitment-exam-kit](https://github.com/CUMT-Alethic-Insight-Lab/recruitment-exam-kit)，
不再从平台的 `exam_kit/` 打包。先检出并验证与平台配套的套件 commit/tag，再将
`EXAM_KIT_DIR` 设为含 `session_receiver.py` 的**绝对目录**（Git Bash 使用 `P:/...`
或 `/p/...` 路径；不是旧 monorepo 根目录）：

```bash
# 仅为部署命令模板；须按发布审批流程执行，本次分仓不运行部署
LAB_HOST=<user@host> SSH_KEY=<私钥路径> \
  EXAM_KIT_DIR=/absolute/path/to/recruitment-exam-kit \
  bash server/deploy/push-lab.sh
```

脚本在任何 SSH 上传之前检查该目录和接收机文件；缺失即退出，不自动克隆、不下载
未锁定版本，也不回退读取旧工作区。应用打包范围仍为 `app static requirements.txt`，
接收机目标路径、systemd 单元、服务重启和健康检查保持不变。
`push-server.sh` 不打包套件，无需 `EXAM_KIT_DIR`；接收机分仓本身不改变考试代理，
成员运行隔离的 nginx 模板变更另行审查、发布，不代表生产配置已变更。

发布前记录平台 commit/tag、套件 commit/tag、安装包版本/SHA256，分别运行两仓测试，
并在隔离环境验证登录、交卷、报告及使用到的 LAN/P2P 通路。成员 CLI/MCP 属于内部
成员产品的同包 infra，不是考试运行依赖，不随考试服务或接收机打包。

考试新库只创建考试表及历史账号/资料兼容表，不再创建 `org_*`、`service_request`
或 `service_request_review`。启动旧库不删除、迁移或同步旧组织表和真实账号；旧组织
数据仍留在原库，不能据此宣称成员数据已经迁移。成员产品必须使用独立运行环境、
数据库和账号生命周期，真实数据迁移需另行审计审批。考试交卷的
`/api/internal/ingest-staged` 仍仅在 authoritative 进程挂载，不属于成员内部 API。

回滚应用时恢复旧 `current`；接收机当前是原地覆盖而非 release 软链，必须从之前记录的
套件 commit/tag 恢复 `/srv/alethic/receiver/session_receiver.py` 并重启接收机，不能只
回滚平台就宣称两者均回滚。真实部署凭据与接收数据不进入任一公共仓。
源码移除的回滚走 revert PR，原本地考试套件目录保留。

## 安装回收定时器

`app.maintenance` 会删除 `expires_at` 已过期的批次数据（uploads 目录、
exam_session、application 等行，见 `app/maintenance.py`），并把批次置为
`closed`，可安全重复执行。用 systemd timer 每天跑一次：

```bash
sudo cp deploy/alethic-recruitment-purge.service /etc/systemd/system/
sudo cp deploy/alethic-recruitment-purge.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now alethic-recruitment-purge.timer
```

验证（应看到 timer 处于 active，并列出下次触发时间）：

```bash
systemctl list-timers alethic-recruitment-purge.timer
journalctl -u alethic-recruitment-purge.service -n 20   # 查看最近一次回收摘要
```

手动立即跑一次：`sudo systemctl start alethic-recruitment-purge.service`。

## 安装暂存转发定时器（云端 edge）

「静态优先云端 + 动态优先 lab」架构下，云端 VPS 以 `ALE_THIC_ROLE=edge`
运行：交卷端点不写主库，multipart 暂存 `data/staging/{session_id}/` 并响应
`pending_sync`；本定时器每 30min 跑 `app.staging_forward`，探 lab 可达后逐个
POST 到 lab 的 `/api/internal/ingest-staged`（`X-Staging-Secret` 共享密钥），
lab 应答成功即删暂存（云端不留数据），lab 不可达本轮整体跳过。

env 需在 `/etc/alethic-recruitment.env` 追加：

```
ALE_THIC_ROLE=edge
LAB_ORIGIN_URL=https://lab-origin.alethicinsight.com  # 注意：不带 /recruitment 前缀，lab 的 API 挂在根路径
STAGING_SECRET=<与 lab 一致的强随机密钥>
# lab 回源若挂 CF Access：
CF_ACCESS_CLIENT_ID=...
CF_ACCESS_CLIENT_SECRET=...
```

lab（authoritative）侧同 env 文件配 `STAGING_SECRET` 即自动挂载收口端点；
lab 侧如需 exam-archive 即时备份再配 `ARCHIVE_ENABLED=1` /
`ARCHIVE_REPO_DIR` / `ARCHIVE_GITHUB_TOKEN`。

```bash
sudo cp deploy/alethic-recruitment-forward.service /etc/systemd/system/
sudo cp deploy/alethic-recruitment-forward.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now alethic-recruitment-forward.timer
```

手动立即跑一次：`sudo systemctl start alethic-recruitment-forward.service`。

## 验证

```bash
curl -s https://<主站域名>/recruitment/api/health
curl -s -o /dev/null -w '%{http_code}\n' https://<主站域名>/recruitment/  # GET 空库首页应 200，不重定向；不用 -I（HEAD）
systemctl status alethic-recruitment
journalctl -u alethic-recruitment -n 50
```

## 注意

- `ADMIN_TOKEN`、密码等敏感信息只放 `/etc/alethic-recruitment.env`，不要写入仓库。
- 换 token / 改环境变量：编辑 env 文件后 `sudo systemctl restart alethic-recruitment`。
- 回滚：把 `current` 软链指回上一个 release 并重启服务。
- 真实主机地址/账号/密钥路径等运维细节见 org 私有仓 **infra-handoff**。

# Recruitment Exam Platform · 招新机试平台

Online machine-test platform for **CUMT Alethic Insight Lab** recruitment: candidates solve problems on **their own computers** with AI tools (Kimi Code or opencode); on submission, the local exam kit uploads the AI session **after cleaning**, and reviewers grade the cleaned trace in the web console.

中国矿业大学 **Alethic Insight** 实验室招新使用的在线机试平台：考生在**自己的电脑**上用 AI 工具（Kimi Code 或 opencode）作答，本地考试端在交卷时把 AI 会话**清洗后**上传，评审在网页端按清洗后的轨迹打分。

## For Candidates · 对考生的话

This repository is public so that candidates can **audit the session-cleaning code** themselves.

本仓库公开，目的是让考生可以**亲自审查会话清洗代码**。

- We only upload the **cleaned** session record — thinking processes and tool-output bodies are removed.
- We never read or upload any other files on your computer.
- The cleaning rules are covered by tests; if you find a problem, please open an Issue.

我们只上传**清洗后**的会话记录（去除思考过程与工具输出正文），不读取、不上传你电脑里的其他文件。清洗规则有测试覆盖，发现问题欢迎提 Issue。

## Repository Layout · 仓库结构

| Path | English | 说明 |
| --- | --- | --- |
| `server/` | Platform backend and admin console (FastAPI + SQLite + vanilla HTML/JS) | 平台后端与管理端（报名 / 账号 / 问卷 / 面试评审 / 题库抽题 / 交卷暂存转发） |
| `exam_kit/` | Candidate exam kit, pure Python standard library, plus the installer | 考生机试套件（纯 Python 标准库）与安装器 |
| `infra/interface/alethicinsight-cli/` | One public interface distribution: CLI and local stdio MCP | 同一 `alethicinsight-cli` 发行包/版本，提供 `alethicinsight-cli` 与 `alethicinsight-mcp` 两个入口；只读与草稿，最终提交在可信网页完成 |
| `docs/` | Design and flow documents | 方案文档（`platform_flow.md` 平台流程；`agent-interface/` 成员事务与 Agent 接口设计草案） |

## Session Cleaning · 会话清洗

| Entry point | Role | 作用 |
| --- | --- | --- |
| `exam_kit/cleaner.py` | Client-side cleaning: export AI session, strip thinking/tool output, produce review Markdown | 考生端清洗：导出 AI 会话 → 去除思考/工具输出 → 生成评审用 md |
| `server/app/cleaned_report.py` | Server-side rebuild: `cleaned.jsonl` → Markdown report for admin download | 服务端重建：把云端暂存的 `cleaned.jsonl` 还原为同构 Markdown 报告 |

## Tests · 测试

从仓库根连续执行；括号中的子 shell 不改变当前终端目录。

```bash
# Server / 服务端
(cd server && python -m pip install -r requirements.txt && python -m pytest tests -q)

# Exam kit / 考生端
(cd exam_kit && python -m pytest -q)
```

## Download · 机试包下载

| Item | Value |
| --- | --- |
| Installer | [AlethicInsight-ExamKit-2026-setup.exe](https://dl.alethicinsight.com/AlethicInsight-ExamKit-2026-setup.exe) |
| SHA256 | `8c2dea2a1269d62ad1abb218dac4f4be8e2e95a75c7c34cd57d2bf157b1ebd8b` |

Verify after download / 下载后请校验：

```powershell
certutil -hashfile AlethicInsight-ExamKit-2026-setup.exe SHA256
```

## Architecture · 架构

```
考生电脑（exam_kit，纯 Python 标准库，无三方依赖）
  ├─ exam_server.py    本地机试服务（发题/换题/交卷，127.0.0.1:8899）
  ├─ cleaner.py        会话清洗：导出 AI 会话 → 去除思考/工具输出 → 生成评审用 md
  └─ session_receiver.py  实验室局域网接收机（upload_mode=lan 时收清洗件）
        │  交卷：HTTPS 上传（默认）/ P2P 直连 / 局域网接收机
        ▼
云端 VPS（server，FastAPI + SQLite，ROLE=edge）
  ├─ 招新主站：报名 / 账号 / 问卷 / 面试评审 / 题库抽题
  └─ 交卷暂存转发：multipart 暂存 → 定时转发 lab 收口（云端不留数据）
        ▼
实验室小主机（lab，ROLE=authoritative）
  └─ 权威库 + ingest-staged 收口 + 即时归档
```

## Related Repositories · 相关仓库

| Repository | English | 说明 |
| --- | --- | --- |
| [join-us](https://github.com/CUMT-Alethic-Insight-Lab/join-us) | New-member hub: join process, preparation guide, downloads | 新成员入口：招新流程、准备建议、机试包下载 |
| [open-onboarding](https://github.com/CUMT-Alethic-Insight-Lab/open-onboarding) | Onboarding in depth: hands-on practice after joining | 深入上手：入组后的练手任务与贡献流程 |

## Private Repositories · 私有仓库（org 内部）

以下内容不随本仓公开，维护在 org 私有仓：

| Repository | 内容 |
| --- | --- |
| `question-bank` | 真实机试题库与解析校验（本仓 `server/tests/fixtures/` 仅有合成夹具） |
| `infra-handoff` | 仅私有运维资料：真实主机地址、账号、密钥路径与运维排障记录；不承载公共 CLI/MCP 源码 |
| `exam-archive` | 考生活档（清洗件 md / 仓库链接 / 附件） |

## Public Interface · 公共接口

CLI 与 MCP 同属 infra，单仓单发行包单版本；在本地 Python 3.10+ venv 从仓库根安装：

```sh
python -m pip install ./infra/interface/alethicinsight-cli
alethicinsight-cli --help
alethicinsight-mcp --help
```

新客户端配置使用 `ALETHICINSIGHT_API_BASE_URL`（服务根，不含 `/api/v1`）与 `ALETHICINSIGHT_CONFIG_DIR`；旧 `ALETHIC_API_BASE_URL`、`ALETHIC_BASE_URL`、`ALETHIC_CONFIG_DIR` 仅为兼容别名。授权 API `/auth/cli/*` 不随发行名改动。最终提交只能由用户在可信网页确认，MCP 不提供审批或正式提交工具。

- [本地 MVP 手册](docs/AGENT_INTERFACE_MVP.md)
- [仓库职责与公开边界](docs/REPOSITORY_BOUNDARIES.md)
- [工作区保全与迁移清单](docs/WORKSPACE_MIGRATION.md)

`Alethic-Insight-Frontend-Templates` 不在此次整理范围；`E:/projects/Aletheion` 仅作历史来源，不作 monorepo。当前不拆 exam-kit、不新建 MCP 仓、不部署生产；迁移先保全 P/E 两处未提交内容，再复制验证，最后人工切换。

## License · 许可与归属

CUMT Alethic Insight Lab. Recruitment materials in the pages remain the property of the lab.

CUMT Alethic Insight Lab。页面中的招新素材版权归实验室所有。

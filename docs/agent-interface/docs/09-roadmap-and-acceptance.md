# 09 · 产品隔离与验收：兼容导航

成员独立仓的安装、标准测试、单包 CLI/MCP 与合成闭环验收以[新成员仓](https://github.com/CUMT-Alethic-Insight-Lab/alethicinsight-member-platform#readme)的实际记录为准。本页仅保留旧路径，不复制成员验收规范或沿用历史通过数。

考试仓执行 `python -m pytest server/tests -q` 及文档链接检查。新成员仓发布与验证完成前不应合并本拆仓 PR；同仓隔离已合并不等于独立仓已发布，更不等于生产或真实数据已迁移。见[迁移历史](../../migration.md)、[工作区门禁](../../WORKSPACE_MIGRATION.md)与[导航索引](../README.md)。

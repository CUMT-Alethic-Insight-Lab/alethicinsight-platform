# 02 · 架构、事实来源与解耦边界：兼容导航

成员架构与实现由独立[成员仓](https://github.com/CUMT-Alethic-Insight-Lab/alethicinsight-member-platform#readme)维护。本页仅保留旧路径，不要求在考试服务注册组织路由或复用身份与数据库。

CLI/MCP 同包归成员内部 infra，考试 `server/` 与成员进程、DB、会话独立。详见[产品边界](../../REPOSITORY_BOUNDARIES.md)和[导航索引](../README.md)；源码分仓不是生产部署证明。

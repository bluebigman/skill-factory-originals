---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: process-trace-analyzer
name: process-trace-analyzer
displayName: 系统进程 端口容器 文件溯源排查
description: 追踪进程、端口、容器或文件的启动来源，生成溯源报告，辅助定位异常与排查系统问题。
version: 1.0.3
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/process-trace-analyzer
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: TraceForge Studio
agent_created: true
trigger_words: ["进程溯源", "端口追踪", "启动来源分析", "异常进程排查", "文件来源追溯", "进程来源", "端口占用来源", "启动项分析"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# 进程溯源分析器（Process Trace Analyzer）

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 能力项 | 说明 | 典型输出 |
|--------|------|----------|
| 进程溯源 | 根据 PID 或进程名，逆向定位启动它的父进程链、启动命令行、启动时间 | 进程树 + 启动命令 + 父进程链 |
| 端口追踪 | 根据端口号定位监听该端口的进程，并回溯该进程的启动来源 | 端口 ↔ 进程 ↔ 启动来源 映射 |
| 容器来源分析 | 根据容器 ID 或名称，定位其镜像来源、启动命令、编排文件（如 docker-compose） | 容器元数据 + 启动配置来源 |
| 文件来源追溯 | 根据文件路径，判断该文件由哪个进程创建/修改，以及该进程的启动来源 | 文件操作记录 + 关联进程链 |
| 异常进程排查 | 识别可疑进程（如无父进程、父进程已退出、启动路径异常），输出风险提示 | 风险等级 + 可疑特征列表 |

### 1.2 不能做什么（明确边界）

| 限制项 | 说明 |
|--------|------|
| 不做实时监控 | 本 Skill 只做**静态溯源分析**，不提供持续监控或告警能力 |
| 不跨主机追踪 | 仅分析当前主机内的进程/文件/端口关系，不追踪网络跨主机的调用链 |
| 不保证数据完整性 | 如果系统日志（如 auditd、syslog）未开启，部分历史溯源信息可能缺失 |
| 不做自动处置 | 只输出分析报告，不执行 kill、rm、iptables 等变更操作 |
| 不识别加密流量内容 | 端口追踪仅定位到进程，不解析 TLS/SSH 等加密载荷 |

### 1.3 适用对象

- 系统运维工程师：排查端口冲突、异常进程占用资源
- 安全应急响应人员：定位可疑进程的启动来源
- DevOps 工程师：确认容器/服务的启动配置来源
- 开发人员：调试本地服务启动异常


## 许可证（License）

```text
MIT License

Copyright (c) 2026 SkillForge Lab

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```
<!-- professional-license-embedded -->

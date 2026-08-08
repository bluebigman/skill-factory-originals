---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: process-trace-analyzer
name: process-trace-analyzer
displayName: 进程溯源 异常定位 系统排查
description: 追踪进程、端口、容器或文件的启动来源，生成溯源报告，辅助定位异常与排查系统问题。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/process-trace-analyzer
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: "TraceForge"
agent_created: true
trigger_words: ["进程溯源", "端口追踪", "启动来源分析", "异常进程排查", "文件来源追溯", "容器溯源", "进程启动链"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# process-trace-analyzer 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| **输入处理** | 接受用户提供的进程列表、端口占用信息、容器元数据、文件路径、系统日志片段、URL（指向日志或配置仓库） | 无法直接连接目标系统执行实时命令；无法访问未提供的私有系统 |
| **溯源分析** | 基于输入数据推断进程启动链、父进程关系、端口与进程的关联、容器镜像来源、文件创建者 | 无法验证推断结果的真实性；无法获取系统未暴露的隐藏进程或内核级信息 |
| **报告生成** | 生成结构化溯源报告，包含时间线、关联关系图（文本描述）、可疑点标注 | 无法生成可视化图形文件（如 PNG/SVG），仅输出 Markdown 或 JSON 格式 |
| **批量处理** | 支持一次提交多条记录（如多个 PID 或端口），批量输出分析结果 | 单次处理超过 500 条记录时性能下降，建议分批 |
| **置信度标注** | 对每项推断结果标注置信度（高/中/低），对缺失信息标注 `[需核实:字段]` | 不会对未经验证的信息给出确定性结论 |

### 1.2 适用对象

- **系统运维人员**：排查异常进程、定位端口冲突来源
- **安全分析人员**：追踪可疑进程的启动链，识别潜在入侵痕迹
- **容器平台管理员**：分析容器启动来源、镜像依赖关系
- **开发人员**：定位本地开发环境中端口被占用或文件被锁定的原因

### 1.3 输入要求速查

| 输入类型 | 格式要求 | 示例 |
|----------|----------|------|
| 进程信息 | `PID 进程名 启动时间 父PID` | `1234 nginx 2025-01-15 10:22:33 1` |
| 端口占用 | `端口号 协议 PID 进程名` | `8080 TCP 5678 java` |
| 容器信息 | `容器ID 镜像名 启动命令 创建时间` | `abc123 nginx:latest "nginx -g daemon off;" 2025-01-15 09:00:00` |
| 文件路径 | 绝对路径 + 可选元数据 | `/usr/local/bin/malware --config=/tmp/x.conf` |
| 日志片段 | 包含进程启动或连接记录的文本 | `Jan 15 10:22:33 host systemd[1]: Started nginx.service.` |


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

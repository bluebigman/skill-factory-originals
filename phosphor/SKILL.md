---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: phosphor
name: phosphor
displayName: 事件追踪 运行时探针 性能观测
description: 基于DTrace的Ruby运行时事件采集与结构化输出工具
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/phosphor
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 独立技能工坊
agent_created: true
trigger_words: ["phosphor", "dtrace", "ruby事件", "运行时追踪", "性能探针", "事件采集"]
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

# phosphor — 基于 DTrace 的 Ruby 运行时事件采集与结构化输出

## 一、能力边界（一页纸速查卡）

### 能做什么

| 编号 | 能力项 | 说明 | 输入示例 | 输出示例 |
|------|--------|------|----------|----------|
| 1 | 事件数据采集 | 将用户提供的 Ruby 进程信息、DTrace 脚本或事件描述转换为结构化结果 | `ruby_app.rb` 进程 PID 1234 | `{ "pid": 1234, "events": [...] }` |
| 2 | 关键信息识别 | 从原始输入中提取进程名、方法调用、内存分配、GC 周期等关键字段 | DTrace 输出文本 | 字段化 JSON 记录 |
| 3 | 约定格式输出 | 按用户指定的格式（JSON / YAML / 表格）生成结果 | `--format json` | 标准 JSON 文档 |
| 4 | 置信度标注 | 对推断字段标注置信水平，不确定时显式提示 | 部分缺失的调用栈 | `"confidence": 0.72` |
| 5 | 批量处理 | 支持多文件、多 PID、多时间窗口的批量事件分析 | 日志目录路径 | 汇总报告 |

### 不能做什么

- 不能修改 Ruby 程序源码或注入代码
- 不能在没有 DTrace 权限的环境下采集数据（需 root 或特定权限）
- 不能跨平台运行（仅限支持 DTrace 的 macOS / Solaris / BSD）
- 不能实时监控——只做离线分析，不提供持续流式输出
- 不能自动修复性能问题，仅定位事件发生点

### 适用对象

- Ruby 应用开发者（排查性能瓶颈）
- SRE / 运维工程师（生产环境事件追踪）
- 性能调优顾问（批量分析多个进程）


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

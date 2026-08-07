---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: chronic
name: chronic
displayName: 时间语义解析 日期转换 批量识别
description: 将自然语言日期描述解析为结构化时间数据，支持多种格式与批量处理。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/chronic
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge Studio
agent_created: true
trigger_words: ["chronic", "日期解析", "自然语言日期", "时间转换", "日期识别", "时间语义", "日期归一化"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# chronic — 自然语言日期解析 Skill

## 一、能力边界：速查卡

| 维度 | 说明 |
|------|------|
| **能做** | 解析中文/英文自然语言日期描述；支持相对日期（"三天后"）；支持绝对日期（"2024年3月15日"）；支持模糊日期（"下个月初"）；支持批量输入（数组/换行分隔）；输出 ISO 8601 结构化时间对象 |
| **不能做** | 不解析时区偏移推算（仅标记时区字段）；不处理农历日期转换；不推断语义模糊的"大约"类描述（如"大概中午"）；不执行日期运算（如"加两周"需先解析再自行计算）；不处理非日期实体（如"第3季度"需先归一化为"Q3"） |
| **适用对象** | 需要从用户输入中提取时间信息的对话系统、任务调度器、日志分析工具、数据清洗管道 |

**输入限制**：单条描述不超过 200 字符；批量输入不超过 100 条/次；超出部分截断并返回截断警告。

**输出格式**：`{ "parsed": true/false, "value": "YYYY-MM-DDTHH:mm:ss", "confidence": 0.0-1.0, "original": "用户输入原文", "warnings": [] }`


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

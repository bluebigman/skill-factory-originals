---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: internship-daily-log
name: internship-daily-log
displayName: 实习日志 结构化整理 记录归档
description: 将杂乱实习笔记转换为结构化日志，支持批量处理与置信度标注。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/internship-daily-log
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LogForge Studio
agent_created: true
trigger_words: ["internship daily log", "实习日志", "实习记录", "工作日志整理", "daily log"]
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

# 实习日志结构化整理 Skill（internship-daily-log）

## 一、能力边界速查卡

本 Skill 面向需要将非结构化实习笔记、工作流水账、零散记录转换为统一格式日志的用户，包括实习生、应届生、职场新人及其带教导师。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入 | 用户粘贴的文本、上传的 .txt/.md/.docx 文件、可访问的 URL 内容 | 无法访问需登录验证的私有系统、无法解析图片中的手写文字 |
| 处理 | 识别日期、任务描述、负责人、状态、产出物、阻塞项等关键字段 | 不推断未提及的隐含信息，不补充用户未提供的上下文 |
| 输出 | 生成 Markdown 表格、JSON 结构化数据、纯文本清单三种格式 | 不生成图表、不自动发送邮件、不写入外部数据库 |
| 批量 | 支持一次处理多条记录（最多 50 条/批次） | 超过 50 条需分批处理，不支持流式输入 |
| 自定义 | 可指定日期范围过滤、按状态筛选、自定义字段别名 | 不支持完全自由格式的模板引擎，字段名需在预设范围内 |

**输入要求**：每条记录至少包含时间（日期或时刻）和事件描述，否则无法生成有效条目。

**输出格式**：默认输出 Markdown 表格；可选 JSON（含 `records` 数组）或纯文本清单。


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

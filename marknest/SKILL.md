---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: marknest
name: marknest
displayName: 文档巢穴 格式转换 信息提取
description: 将用户提供的文件或链接，转换为规范、可复用的结构化输出。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/marknest
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingForge
agent_created: true
trigger_words: ["PDF转文档", "marknest", "格式转换", "文档处理", "信息提取"]
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

# MarkNest 技能手册

## 一、能力边界速查卡

本技能用于处理用户提交的数据、文件或 URL，将其转化为结构化的、可复用的输出结果。以下表格明确了本技能的适用范围与限制。

| 维度 | 说明 |
| :--- | :--- |
| **核心任务** | 解析输入内容，识别关键信息，按约定格式输出结构化结果。 |
| **输入来源** | 用户直接粘贴的文本数据、上传的本地文件（如 PDF、TXT、MD）、可访问的 URL 链接。 |
| **输出形式** | 标准 Markdown 文档、JSON 数据格式、或用户指定的自定义模板。 |
| **批量处理** | 支持一次提交多个文件或 URL，按顺序逐一处理并汇总输出。 |
| **能力边界** | 不执行代码、不访问需登录授权的私有系统、不进行事实性核查（如验证新闻真伪）。 |
| **适用对象** | 需要快速整理文档要点、提取关键字段、或转换文档格式的个人开发者、研究人员及办公人员。 |

**不能做的事项：**
- 不处理图像中的文字（OCR 功能需外部配合）。
- 不修改原始文件，仅生成新的输出内容。
- 不提供法律、医疗或金融等专业领域的权威建议。


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

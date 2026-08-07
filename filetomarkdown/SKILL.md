---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: filetomarkdown
name: filetomarkdown
displayName: 文档转写 格式转换 内容提取
description: 将用户提供的文件或链接转为结构化Markdown，保留关键信息并标注置信度。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/filetomarkdown
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 格式工坊
agent_created: true
trigger_words: ["filetomarkdown", "转Markdown", "文档转写", "格式转换", "内容提取"]
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

# filetomarkdown 技能文档

## 一、能力边界速查卡

本技能用于将用户提供的各类数据源（文件、链接、文本片段）转换为结构化的 Markdown 文档。以下用一页纸说明能做什么、不能做什么。

| 维度 | 说明 |
|------|------|
| **输入类型** | 本地文件（PDF、TXT、DOCX、CSV、JSON）、网页 URL、纯文本粘贴 |
| **输出格式** | 标准 Markdown（.md），含标题层级、表格、代码块、列表 |
| **核心能力** | ① 解析输入内容 ② 识别关键字段 ③ 按约定结构输出 ④ 置信度标注 ⑤ 批量处理 |
| **适用对象** | 需要将非结构化文档转为可读、可维护的 Markdown 格式的个人或团队 |
| **不处理** | 不执行 OCR 图像文字识别（仅处理文本层）；不翻译内容；不生成摘要；不修改原始文件 |
| **限制条件** | 单个文件不超过 10MB；URL 需可公开访问；加密或损坏文件无法解析 |


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

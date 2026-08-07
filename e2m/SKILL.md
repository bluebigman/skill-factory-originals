---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: e2m
name: e2m
displayName: 文档转写 多格式转换 结构化整理
description: 将各类文件或链接转为结构化Markdown，保留关键信息。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/e2m
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨工坊
agent_created: true
trigger_words: ["e2m", "转markdown", "转md", "文件转换", "格式转换", "转文档", "链接转md"]
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

# e2m — 多格式转 Markdown 技能手册

## 一、能力边界（一页纸速查卡）

| 维度 | 说明 |
|------|------|
| **能做的事** | 将文本文件（.txt/.md/.csv）、富文本（.docx/.rtf）、网页链接（http/https）、剪贴板内容、PDF 文本层内容转换为结构化 Markdown |
| **不能做的事** | 无法解析扫描版 PDF（无文本层）、无法处理加密/损坏文件、无法执行 OCR 识别、无法转换音频视频、无法保留原文件中的复杂排版（如文本框坐标、艺术字效果） |
| **适用对象** | 需要快速整理资料的研究人员、需要归档网页内容的编辑、需要统一笔记格式的知识管理爱好者、需要批量转换文档的办公人员 |
| **不适用对象** | 需要像素级还原原版式的出版行业、需要处理手写笔记的用户、需要转换超过 50MB 超大文件的场景 |

**输入限制**：单次处理文件大小 ≤ 20MB；链接长度 ≤ 2048 字符；支持的文件编码为 UTF-8/GBK/GB2312。


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

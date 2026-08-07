---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: awesome-claude-notes
name: awesome-claude-notes
displayName: 知识笔记 结构化整理 信息萃取
description: 将零散资料转化为结构化笔记，支持批量处理与置信度标注。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/awesome-claude-notes
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: NoteForge Studio
agent_created: true
trigger_words: ["awesome claude notes", "知识笔记", "笔记整理", "信息结构化", "资料萃取"]
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

# awesome-claude-notes — 知识笔记结构化整理 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | ✅ 能做 | ❌ 不能做 |
|------|--------|----------|
| 输入类型 | 用户粘贴的文本、上传的 `.txt` / `.md` / `.csv` 文件、公开 URL 指向的文本内容 | 图片 OCR、音视频转写、需登录的私有系统内容 |
| 处理能力 | 提取关键信息、按字段结构化、批量处理多条记录、自定义输出模板 | 语义理解之外的推理判断、跨语言精准翻译 |
| 输出形式 | Markdown 表格、JSON 对象、键值对清单、分级摘要 | 直接写入用户本地文件系统（需用户自行复制保存） |
| 质量保障 | 对每项提取结果标注置信度（高/中/低） | 对缺失信息进行猜测或编造 |

### 1.2 适用对象

- **适用**：需要将会议纪要、网页摘录、文献片段、访谈记录等文本资料整理为统一格式笔记的个人或团队。
- **不适用**：需要深度语义分析、情感判断、或对图像/音频直接解析的场景。

### 1.3 输入与输出规格

| 项目 | 规格说明 |
|------|----------|
| 输入来源 | 用户直接提供文本 / 上传文件 / 提供可公开访问的 URL |
| 输出格式 | 默认 Markdown 表格 + 字段键值对；可切换为 JSON |
| 字段结构 | `编号`、`原文摘要`、`关键实体`、`主题分类`、`置信度`、`备注` |
| 批量上限 | 单次处理不超过 50 条独立记录（超出则分批提示） |


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

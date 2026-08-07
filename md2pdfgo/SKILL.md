---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: md2pdfgo
name: md2pdfgo
displayName: Markdown转PDF 文档生成 格式转换
description: 将Markdown内容转换为PDF文档，支持批量处理与自定义样式。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/md2pdfgo
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["md2pdfgo", "markdown转pdf", "md转pdf", "文档转换", "pdf生成"]
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

# md2pdfgo — Markdown 转 PDF 转换器

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|--------|----------|
| 输入格式 | Markdown 文本、`.md` 文件、指向 Markdown 的 URL | 二进制格式（DOCX、XLSX 等）直接输入 |
| 转换能力 | 标准 Markdown 语法 → PDF 渲染 | 复杂 LaTeX 公式、SVG 矢量图渲染 |
| 样式控制 | 页边距、字体大小、代码块主题 | 逐像素级排版微调 |
| 批处理 | 多文件批量转换，输出独立 PDF | 合并多个 MD 为单一 PDF（需额外参数） |
| 输出 | 本地 PDF 文件路径 | 云端存储直传 |

### 1.2 适用对象

- **内容创作者**：将技术文档、博客草稿转为 PDF 分发
- **开发者**：生成 API 文档、README 的 PDF 版本
- **办公人员**：将会议纪要、报告草稿转为正式 PDF

### 1.3 输入参数速查

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `input` | string | 是 | — | Markdown 内容、文件路径或 URL |
| `output` | string | 否 | `output.pdf` | 输出 PDF 文件名 |
| `style` | string | 否 | `default` | 样式模板：`default` / `compact` / `formal` |
| `margin` | number | 否 | `20` | 页边距（毫米） |
| `fontsize` | number | 否 | `11` | 正文字号（pt） |
| `batch` | boolean | 否 | `false` | 批量模式开关 |


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

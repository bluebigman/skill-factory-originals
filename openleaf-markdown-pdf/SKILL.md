---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: openleaf-markdown-pdf
name: openleaf-markdown-pdf
displayName: 分页文档 PDF 转换排版工具
description: 将 Markdown 转为分页 PDF，适配报告、合同、标书等正式文档。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/openleaf-markdown-pdf
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LeafForge Studio
agent_created: true
trigger_words: ["PDF转文档", "markdown转pdf", "md转pdf", "分页pdf", "文档排版"]

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

# openleaf-markdown-pdf — 分页文档 PDF 转换排版工具

## 一、能力边界：一页纸速查卡

### 1.1 核心能力（能做）

| 序号 | 能力项 | 说明 | 适用场景 |
|------|--------|------|----------|
| 1 | Markdown → PDF 转换 | 将标准 Markdown 文本转换为 PDF 文件 | 技术文档、会议纪要、项目报告 |
| 2 | 分页控制 | 支持手动分页符（`\newpage` 或 `---` 配置） | 合同章节、标书分节、报告分章 |
| 3 | 样式定制 | 支持页眉、页脚、页码、字体、边距设置 | 正式公文、学术论文、商业提案 |
| 4 | 目录生成 | 自动提取标题层级生成可点击目录 | 用户手册、操作指南、长篇报告 |
| 5 | 批量转换 | 支持多文件批量处理，统一输出目录 | 文档归档、批量报告生成 |

### 1.2 能力边界（不能做）

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不支持复杂表格 | 嵌套表格、合并单元格等复杂结构会降级为纯文本 |
| 2 | 不支持动态图表 | 无法将交互式图表（如 Plotly）嵌入 PDF |
| 3 | 不支持加密 PDF | 输出文件不设密码保护 |
| 4 | 不支持扫描件 OCR | 输入必须是可编辑的 Markdown 文本 |
| 5 | 不支持实时预览 | 转换过程为一次性批处理，无交互界面 |

### 1.3 适用对象

- **适合**：需要生成正式分页文档的开发者、文档工程师、项目经理
- **不适合**：需要复杂排版（如杂志样式）、动态交互内容的场景


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: pdf-to-markdown
name: pdf-to-markdown
displayName: PDF转Markdown 表格结构保留
description: 将PDF解析为带表格结构的Markdown，保留版式与关键信息。
version: 2.0.7
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/pdf-to-markdown
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["pdf转markdown", "pdf转md", "pdf表格提取", "pdf解析", "pdf转文档", "pdf转markdown表格", "pdf结构化提取"]
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

# PDF 转 Markdown 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输出示例 |
|--------|------|----------|
| 文本提取 | 从 PDF 中提取正文文本内容 | `这是一段提取出来的文本。` |
| 表格结构还原 | 识别 PDF 中的表格，输出为 Markdown 表格语法 | `\| 列1 \| 列2 \|` |
| 版式保留 | 保留标题层级、列表、粗体/斜体等基础格式 | `## 二级标题` |
| 多页合并 | 将多页 PDF 内容合并为一个 Markdown 文件 | 连续页面的文本按顺序拼接 |
| 图片占位 | 对无法解析的图片输出占位标记 | `![图片](page-3-img-1)` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 扫描件 OCR | 纯图片型 PDF（无文本层）无法直接提取文字，需先进行 OCR 处理 |
| 复杂公式 | 数学公式、化学方程式等特殊符号可能丢失或变形 |
| 加密 PDF | 需要密码的 PDF 无法直接解析，需先解密 |
| 手写内容 | 手写批注、签名等无法识别 |
| 精确排版还原 | 无法做到像素级还原，仅保留逻辑结构 |

### 1.3 适用对象

- 需要将 PDF 报告转为可编辑 Markdown 的文档工程师
- 需要从 PDF 中提取表格数据做进一步分析的数据分析师
- 需要将 PDF 资料整理为知识库内容的个人或团队


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

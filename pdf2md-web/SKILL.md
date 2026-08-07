---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: pdf2md-web
name: pdf2md-web
displayName: 文档转写 结构化提取 置信标注
description: 将PDF或网页转为结构化Markdown，保留关键信息并标注置信度。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/pdf2md-web
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 墨羽工坊
agent_created: true
trigger_words: ["PDF转文档", "PDF转Markdown", "PDF识别", "文字提取", "网页转文档", "文档结构化", "内容转写"]
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

# pdf2md-web 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入示例 | 输出示例 |
|--------|------|----------|----------|
| PDF 转 Markdown | 解析 PDF 文件内容，输出结构化 Markdown | `report.pdf`（含表格、标题） | 带标题层级、表格语法的 .md 文本 |
| 网页转 Markdown | 抓取网页正文，去除导航/广告等噪音 | `https://example.com/article` | 保留正文结构的 Markdown |
| 关键信息保留 | 自动识别文档中的标题、列表、表格、引用块 | 含多级列表的合同文本 | 层级列表 + 表格语法 |
| 置信度标注 | 对识别不确定的内容添加置信度标记 | 扫描件中模糊的文字 | `[置信度:78%] 模糊段落文本` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行 OCR 图像增强 | 对纯图片型 PDF（扫描件无文字层）仅能提取已嵌入的文本层，无法对图片内容做视觉识别 |
| 不处理加密 PDF | 需要密码的 PDF 文件无法解析，需先解密 |
| 不保留复杂排版 | 多栏排版、浮动文本框等复杂布局会按阅读顺序重排，不保证原始视觉位置 |
| 不进行语义总结 | 仅做格式转换，不生成摘要、不提炼观点、不翻译语言 |
| 不处理动态网页 | 依赖 JavaScript 渲染的网页内容（如 SPA 应用）可能抓取不全 |

### 1.3 适用对象

- 需要将合同、论文、报告等 PDF 转为可编辑 Markdown 的办公人员
- 需要将在线文章存档为本地结构化文档的研究者
- 需要批量处理文档并保留来源可信度的内容运营者


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

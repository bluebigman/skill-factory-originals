---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: any2md
name: any2md
displayName: 文档转Markdown 结构化整理 格式转换
description: 将任意输入内容转换为结构化Markdown，保留关键信息并标注置信度。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/any2md
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 墨羽
agent_created: true
trigger_words: ["any2md","PDF转文档","转Markdown","格式转换","文档结构化","文本转MD","内容整理"]
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

# any2md Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入示例 | 输出示例 |
|--------|------|----------|----------|
| 文本转 Markdown | 将纯文本、富文本内容转换为结构化 Markdown | 一段无格式会议纪要 | 带标题层级、列表、加粗的 MD 文档 |
| PDF 内容提取 | 从 PDF 中提取文字内容并结构化 | 扫描版 PDF（需可复制文字） | 按章节拆分的 Markdown |
| 网页内容整理 | 将网页正文提取为干净 Markdown | 新闻文章 URL 或粘贴的网页文本 | 去除导航/广告后的正文 MD |
| 对话记录结构化 | 将聊天记录、访谈内容转为问答或分节格式 | 客服对话记录 | 按话题分组的 Markdown |
| 表格识别 | 识别文本中的表格数据并转为 MD 表格 | CSV 格式数据 | 标准 Markdown 表格 |
| 代码块保留 | 识别代码片段并保留语法高亮标记 | 含 Python 代码的技术文档 | 带 ```python 围栏的 MD |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 图像 OCR | 无法识别图片中的文字，仅处理可复制的文本层 |
| 复杂排版还原 | 无法还原 PDF 中精确的字体、颜色、页眉页脚 |
| 语义理解 | 不进行内容总结、翻译或情感分析 |
| 格式美化 | 不生成 HTML、LaTeX 等其他格式 |
| 加密文件 | 无法处理有密码保护的 PDF 或文档 |

### 1.3 适用对象

- 需要将零散资料整理为统一格式的文档工作者
- 需要将 PDF/网页内容转为可编辑 Markdown 的研究人员
- 需要将对话记录、会议纪要结构化的团队协作人员
- 需要批量处理文本格式转换的开发者


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

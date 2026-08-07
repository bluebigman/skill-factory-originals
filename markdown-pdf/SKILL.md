---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: markdown-pdf
name: markdown-pdf
displayName: 文档转PDF 格式转换 文件处理
description: 将Markdown内容转换为PDF文档，支持文件、URL及批量处理。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/markdown-pdf
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["PDF转文档", "markdown转pdf", "md转pdf", "文档转换", "格式转换"]

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

# Markdown 转 PDF 转换器（markdown-pdf）

## 一、能力边界速查卡

### 1.1 能做什么（5项核心能力）

| 序号 | 能力项 | 说明 | 适用场景示例 |
|------|--------|------|--------------|
| 1 | 数据/文件/URL 输入转换 | 接受用户提供的 Markdown 文本、`.md` 文件路径或远程 URL 地址 | 将本地笔记、GitHub README、在线文档转为 PDF |
| 2 | 关键信息识别与保留 | 自动识别标题层级、代码块、表格、链接、图片引用等 Markdown 元素，并在 PDF 中完整呈现 | 技术文档、项目说明书的格式保真转换 |
| 3 | 结构化输出生成 | 按用户指定的页面尺寸、页边距、字体大小等参数生成 PDF 文件 | 需要特定排版格式的正式文档输出 |
| 4 | 置信度标注 | 对转换过程中无法确定的内容（如损坏的图片链接、不支持的语法）给出明确提示 | 源文件中存在异常元素时的处理 |
| 5 | 批量处理与自定义格式 | 支持一次提交多个文件/URL，并允许自定义输出命名规则、合并方式 | 批量转换多个章节文档为一个完整 PDF |

### 1.2 不能做什么（明确边界）

| 限制项 | 说明 |
|--------|------|
| 不支持复杂排版还原 | 如多栏布局、浮动元素、精确像素级定位等高级排版能力不在本 Skill 范围内 |
| 不执行 OCR 识别 | 输入必须是文本型 Markdown，不接受扫描件或图片型 PDF 的转换 |
| 不处理加密文件 | 受密码保护的 PDF 或加密的 Markdown 文件无法处理 |
| 不保证字体完全一致 | 中文字体在不同系统环境下渲染效果可能存在差异 |
| 不提供在线托管服务 | 本 Skill 仅负责本地转换，不包含文件存储或分享功能 |

### 1.3 适用对象

- **内容创作者**：需要将 Markdown 草稿导出为 PDF 用于发布或分享
- **技术文档维护者**：需要将项目文档、API 说明转换为 PDF 存档
- **学术研究人员**：需要将论文草稿（Markdown 格式）转为 PDF 提交
- **批量文档处理需求者**：需要将多个 Markdown 文件合并为一个 PDF 文件


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

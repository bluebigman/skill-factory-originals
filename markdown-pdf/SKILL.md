---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: markdown-pdf
name: markdown-pdf
displayName: 文档转换 PDF 输出 格式处理
description: 将 Markdown 内容转换为 PDF 文档，支持文件、URL 及批量处理。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/markdown-pdf
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本 Skill 由 AI 辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["PDF转文档", "markdown转pdf", "md转pdf", "文档转换", "格式转换", "导出PDF", "生成PDF"]
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

# Markdown 转 PDF 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 文件转换 | 将本地 `.md` 文件转换为 PDF | `report.md` → `report.pdf` |
| URL 转换 | 抓取远程 Markdown 内容并转换 | GitHub README 链接 → PDF |
| 批量处理 | 一次转换多个文件或 URL | 目录下所有 `.md` 文件 |
| 样式控制 | 支持自定义页眉、页脚、字体、页边距 | 设置 A4 纸、12pt 字体 |
| 目录生成 | 自动为长文档生成可点击目录 | 章节标题自动提取 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不支持复杂排版 | 表格跨页、多栏布局、浮动图片等高级排版无法保证 |
| 不处理加密 PDF | 仅生成新 PDF，不读取或修改已有 PDF |
| 不保留动态内容 | 代码高亮、交互式图表等动态元素会静态化 |
| 不保证字体嵌入 | 依赖系统字体，跨平台查看时可能出现字体替换 |

### 1.3 适用对象

- 需要将技术文档、README、笔记转为 PDF 的开发者
- 需要批量生成报告、手册的内容运营人员
- 需要将在线 Markdown 资源存档的科研人员


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: markdownconverter
name: markdownconverter
displayName: Markdown 格式转换 文档导出 批处理
description: 将 Markdown 文件转换为 HTML、PNG 或 PDF 格式，支持批量处理与自定义样式。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/markdownconverter
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 格式工坊
agent_created: true
trigger_words: ["markdown转换", "md转html", "md转pdf", "md转png", "文档格式转换", "批量转换", "导出文档"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# Markdown 格式转换 Skill 文档

## 一、能力边界速查卡

### 1.1 能做什么

| 序号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| 1 | 格式转换 | 将 Markdown 文件转换为 HTML、PNG、PDF | `report.md` → `report.pdf` |
| 2 | 批量处理 | 一次处理多个文件，支持通配符 | `./docs/*.md` → 批量输出 |
| 3 | 样式定制 | 通过 CSS 或配置项自定义输出样式 | 自定义页眉、字体、主题色 |
| 4 | 目录结构保留 | 转换时保留原有目录层级 | `docs/a/b.md` → `output/a/b.html` |
| 5 | 元数据提取 | 从 Markdown 中提取标题、标签等结构化信息 | 提取 `# 标题` 作为文档名 |

### 1.2 不能做什么

- 不支持 Markdown 以外的输入格式（如 docx、rst 需先自行转换）
- 不处理加密或受密码保护的 PDF 文件
- 不执行 Markdown 内嵌的 JavaScript 代码
- 不保证复杂表格、数学公式在所有输出格式中的完美渲染
- 不提供云端存储或文件托管服务

### 1.3 适用对象

- 需要将技术文档发布为网页的开发者
- 需要将笔记导出为图片分享的知识工作者
- 需要批量生成 PDF 报告的项目管理人员
- 需要统一文档格式的团队协作场景

---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

## 二、触发方式与场景映射

### 2.1 触发词表

| 触发词 | 场景描述 |
|--------|----------|
| markdown转换 | 用户提到需要转换 Markdown 文件 |
| md转html | 明确指定目标格式为 HTML |
| md转pdf | 明确指定目标格式为 PDF |
| md转png | 明确指定目标格式为 PNG 图片 |
| 文档格式转换 | 泛指文档格式转换需求 |
| 批量转换 | 需要一次处理多个文件 |
| 导出文档 | 将 Markdown 内容导出为其他格式 |

### 2.2 场景映射示例

| 用户说 | 实际需求 | 推荐操作 |
|--------|----------|----------|
| "帮我把这份 README 转成网页" | Markdown → HTML | 执行转换，输出 HTML 文件 |
| "这些 md 文件都要转成 PDF" | 批量 Markdown → PDF | 批量处理，逐个输出 PDF |
| "我想把笔记转成图片发朋友圈" | Markdown → PNG | 转换并提示图片尺寸选项 |
| "转换后能保持原来的目录结构吗" | 目录结构保留 | 确认后按原结构输出 |


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: md2pdfgo
name: md2pdfgo
displayName: 文档转换 排版渲染 PDF生成
description: 将Markdown内容转换为PDF文档，支持批量处理与自定义样式。
version: 1.0.3
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/md2pdfgo
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 墨染工坊
agent_created: true
trigger_words: ["md2pdfgo", "markdown转pdf", "md转pdf", "文档转换", "pdf生成", "格式转换", "文档导出"]
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

# md2pdfgo — Markdown 转 PDF 技能手册

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 支持程度 |
|--------|------|----------|
| 单文件转换 | 将单个 `.md` 文件转为 `.pdf` | ✅ 完整支持 |
| 批量转换 | 一次处理多个 Markdown 文件 | ✅ 完整支持 |
| 自定义样式 | 通过 CSS 或主题参数调整排版 | ✅ 支持（需提供样式文件） |
| 目录生成 | 自动提取标题层级生成书签/目录 | ✅ 支持（默认开启） |
| 代码高亮 | 代码块语法着色 | ✅ 支持（内置 20+ 语言） |
| 表格渲染 | Markdown 表格转 PDF 表格 | ✅ 支持（自动调整列宽） |
| 图片嵌入 | 本地/远程图片引用 | ⚠️ 部分支持（远程需联网） |
| 数学公式 | LaTeX 公式渲染 | ⚠️ 需额外启用 `--math` 参数 |
| 加密输出 | 为 PDF 设置密码 | ❌ 不支持 |
| 水印添加 | 文字/图片水印 | ❌ 不支持 |

### 1.2 不能做什么

- 不支持从 PDF 反向转换为 Markdown
- 不支持扫描件 OCR 识别
- 不支持交互式表单生成
- 不支持动态图表（如 ECharts 渲染）
- 不保证复杂嵌套表格的像素级还原

### 1.3 适用对象

- **内容创作者**：将技术文档、博客草稿导出为 PDF 分享
- **开发者**：将 README、API 文档转 PDF 归档
- **办公人员**：将会议纪要、报告草稿转为正式 PDF 文件
- **教育场景**：将讲义、习题集 Markdown 源文件转 PDF 打印


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

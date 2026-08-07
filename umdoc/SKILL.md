---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: umdoc
name: umdoc
displayName: 文档转换 排版输出 格式适配
description: 将Markdown内容转换为LaTeX并生成PDF文档的自动化工具。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/umdoc
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingWei
agent_created: true
trigger_words: ["PDF转文档", "Markdown转PDF", "文档转换", "LaTeX生成", "PDF导出"]
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

# umdoc — Markdown 到 LaTeX 再到 PDF 的转换工具

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 序号 | 能力项 | 说明 | 输入示例 | 输出示例 |
|------|--------|------|----------|----------|
| 1 | 格式转换 | 将 Markdown 文本转换为 LaTeX 源码 | `# 标题` + 正文段落 | `\section{标题}` + `\paragraph{}` |
| 2 | PDF 生成 | 通过 LaTeX 引擎编译生成 PDF 文件 | 转换后的 `.tex` 文件 | 编译完成的 `.pdf` 文件 |
| 3 | 结构保留 | 识别标题层级、列表、表格、代码块等结构 | 嵌套列表、多级标题 | 对应的 LaTeX 环境（`itemize`、`tabular` 等） |
| 4 | 样式映射 | 将 Markdown 的粗体、斜体、行内代码映射为 LaTeX 命令 | `**加粗**`、`` `code` `` | `\textbf{加粗}`、`\texttt{code}` |
| 5 | 批量处理 | 支持一次提交多个 `.md` 文件，逐个转换并输出 | 目录下多个 Markdown 文件 | 每个文件对应的 `.tex` 与 `.pdf` |

### 1.2 不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不处理图片内容 | 图片仅以路径引用形式保留，不做图像识别或重绘 |
| 2 | 不解析复杂数学公式 | 行内公式 `$...$` 与块级公式 `$$...$$` 原样保留，不做语法校验 |
| 3 | 不修复源文档错误 | 源 Markdown 中的语法错误（如未闭合的代码块）会原样传递，不自动纠正 |
| 4 | 不生成目录索引 | 如需目录，需在源文档中手动添加 `[TOC]` 标记，工具会将其转换为 `\tableofcontents` |
| 5 | 不支持自定义模板 | 使用内置的 LaTeX 模板，不开放模板修改接口 |

### 1.3 适用对象

- 需要将技术文档、笔记、报告从 Markdown 转为正式 PDF 的写作者
- 需要批量生成 PDF 版本文档的团队或个人
- 熟悉 Markdown 语法但不熟悉 LaTeX 的用户


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

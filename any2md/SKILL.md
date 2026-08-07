---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: any2md
name: any2md
displayName: 文档转换 格式整理 信息提取
description: 将任意输入内容转换为结构化Markdown，保留关键信息并标注置信度。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/any2md
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 格式工坊
agent_created: true
trigger_words: ["any2md","PDF转文档","转Markdown","格式转换","文档结构化"]
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

# any2md — 文档转 Markdown 结构化处理 Skill

## 一、能力边界速查卡

### 能做（核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 多源输入解析 | 接受用户直接粘贴的文本、上传的文件（PDF/Word/TXT）、或可访问的 URL 链接 |
| 2 | 关键信息识别 | 自动提取标题、段落、列表、表格、代码块、引用等结构化元素 |
| 3 | 格式规范化输出 | 按 Markdown 语法规范生成层级清晰、可读性强的文档 |
| 4 | 置信度标注 | 对识别不确定的内容（如扫描件乱码、表格错位）标注 `[需核实:字段名]` |
| 5 | 批量与自定义 | 支持多文件依次处理，允许用户指定输出字段顺序或自定义模板 |

### 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不处理加密文件 | 密码保护的 PDF/Word 需用户先解除密码 |
| 2 | 不进行语义改写 | 仅做格式转换，不改变原文措辞与语序 |
| 3 | 不识别手写内容 | 手写扫描件需先经 OCR 工具预处理 |
| 4 | 不保证排版像素级还原 | 复杂双栏/图文混排可能丢失原始视觉布局 |
| 5 | 不执行外部命令 | 仅处理用户提供的输入，不主动调用系统命令 |

### 适用对象

- 需要将 PDF 报告转为可编辑 Markdown 的文档工程师
- 需要从网页/文本中提取结构化信息的分析人员
- 需要统一多来源资料格式的知识管理爱好者


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

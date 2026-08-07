---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: arc
name: arc
displayName: 数据整理 信息提取 结构化输出
description: 将用户提供的各类数据源解析为结构化结果，保留关键信息并标注置信度。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/arc
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨
agent_created: true
trigger_words: ["arc", "数据整理", "信息提取", "结构化输出", "数据解析"]
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

# arc — 数据整理与结构化输出 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入类型 | 用户直接粘贴的文本、本地文件路径（.txt/.csv/.json/.md）、可访问的 URL | 需要登录鉴权的私有系统、加密文件、动态渲染的网页 |
| 处理动作 | 解析内容、识别关键实体（人名/日期/金额/编号）、按模板重组字段 | 对内容做主观判断、生成新数据、修改原始文件 |
| 输出形式 | 结构化 Markdown 表格、JSON 对象、CSV 行格式 | 直接写入用户本地文件（需用户自行复制） |
| 批量能力 | 单次请求可处理最多 10 条独立数据项 | 超过 10 条需分批提交 |
| 自定义格式 | 支持用户指定字段名和输出顺序 | 不支持编程式模板（如 Jinja2 表达式） |

### 1.2 适用对象

- 需要从零散资料中快速提取关键字段的运营人员
- 需要将非结构化笔记转为表格数据的分析师
- 需要统一格式汇总多方来源信息的研究助理

### 1.3 输入与输出规格

**输入要求：**
- 文本：直接粘贴，单次不超过 5000 字符
- 文件：提供可访问的本地路径或 URL，文件大小不超过 2MB
- 数据项：每条数据需有明确分隔（换行、逗号、分号均可）

**输出约定：**
- 默认输出 Markdown 表格，字段顺序为：序号、原始内容摘要、提取字段、置信度
- 用户可指定字段结构，例如："请提取姓名、电话、地址"
- 置信度标注规则：≥90% 标 `高`，70%-89% 标 `中`，<70% 标 `低` 并附说明


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

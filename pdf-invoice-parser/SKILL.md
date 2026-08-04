---
slug: pdf-invoice-parser
name: pdf-invoice-parser
displayName: 发票PDF解析 字段提取 数据校验
description: 从PDF发票中提取结构化字段并校验数据一致性。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/pdf-invoice-parser
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinBox
agent_created: true
trigger_words: ["pdf-invoice-parser", "发票解析", "提取发票信息", "PDF发票转数据", "invoice extraction"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# PDF 发票解析器（pdf-invoice-parser）

## 一、能力边界：一页纸速查卡

本 Skill 专注从 PDF 格式的发票文件中提取关键业务字段，并执行基础的一致性校验。它面向需要批量处理发票的财务人员、数据分析师或自动化流程开发者。

| 能力维度 | 支持范围 | 不支持范围 |
| :--- | :--- | :--- |
| **输入格式** | 文本型 PDF（可选中复制文字） | 扫描件、图片型 PDF（需先 OCR） |
| **核心字段** | 发票代码、号码、开票日期、购买方/销售方名称及税号、金额（不含税/税额/价税合计） | 商品明细行项目（仅提取总金额） |
| **文件处理** | 单文件解析 | 批量文件夹扫描、压缩包解压 |
| **输出格式** | Markdown 表格或 JSON 结构 | 直接写入 Excel/数据库（需二次开发） |
| **校验逻辑** | 价税合计 = 金额 + 税额（容差 ±0.01） | 发票真伪查验、税局接口对接 |
| **语言支持** | 中文发票（简体） | 英文、繁体发票 |

**适用对象**：需要快速将 PDF 发票内容转换为可编辑文本数据的个人或团队。不适用于需要核验发票法律效力或进行税务申报的场景。


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

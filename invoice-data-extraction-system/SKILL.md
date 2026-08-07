---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: invoice-data-extraction-system
name: invoice-data-extraction-system
displayName: 票据解析 字段抽取 结构化输出
description: 将发票PDF或图片转为结构化数据，含置信度标注与批量处理。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/invoice-data-extraction-system
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据工坊
agent_created: true
trigger_words: ["发票识别", "票据解析", "invoice data extraction", "发票信息抽取", "OCR结构化"]
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

# 票据解析与字段抽取 Skill 文档

## 一、能力边界速查卡

本 Skill 面向需要从发票类文档（PDF、图片、扫描件）中提取结构化字段的用户，适用于财务对账、报销审核、数据归档等场景。

| 维度 | 说明 |
|------|------|
| ✅ 能做 | 解析 PDF/图片/URL 中的发票文本；抽取关键字段（发票号、日期、金额、税额、购买方/销售方信息）；输出 JSON/CSV 结构化结果；批量处理多文件；对不确定字段标注置信度 |
| ❌ 不能做 | 无法识别手写体（仅限印刷体）；无法处理加密或损坏的 PDF；不提供法律效力的验真服务；不执行任何支付或财务操作 |
| ⚠️ 边界条件 | 单文件不超过 20 页；图片分辨率建议 ≥ 300 DPI；支持中英文发票，其他语种识别率可能下降 |

**适用对象**：需要快速从发票中提取关键信息的财务人员、开发人员、数据分析师。


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

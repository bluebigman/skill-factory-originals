---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: acts-as-money
name: acts-as-money
displayName: 金额字段 货币处理 数据转换
description: 将任意来源的金额数据解析、校验并转换为标准货币结构化结果。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/acts-as-money
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据工坊
agent_created: true
trigger_words: ["acts as money", "金额转换", "货币解析", "money gem", "金额字段处理"]
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

# acts-as-money 技能文档

## 一、能力边界速查卡

本技能面向需要将**非结构化金额信息**（如文本、文件、URL 中的货币数值）转化为**结构化货币数据**的场景。

| 维度 | 说明 |
|------|------|
| **核心用途** | 从用户提供的文本、文件或 URL 中提取金额、币种、日期等关键字段，输出为标准化 JSON 结构 |
| **输入类型** | 纯文本、CSV/JSON 文件、网页 URL（需可公开访问） |
| **输出格式** | JSON 对象数组，每个对象包含 `amount`、`currency`、`date`、`confidence` 字段 |
| **批量能力** | 支持单次输入多条记录，自动逐条解析 |
| **自定义格式** | 可通过参数指定输出字段子集或字段别名 |

### 能做（5 项）

1. 解析混合文本中的金额数值（支持千分位、小数点、正负数、括号负数表示法）
2. 识别常见货币符号与 ISO 4217 三字母代码（USD、EUR、CNY、JPY 等）
3. 从文件（CSV/JSON）或公开 URL 中批量提取金额数据
4. 对解析结果标注置信度（高/中/低），低置信度时给出原因
5. 按用户指定的字段顺序或别名输出结果

### 不能做（5 项）

1. 不执行实时汇率换算（仅保留原始币种与数值）
2. 不访问需要登录或认证的私有 URL
3. 不处理扫描件或图片中的金额（OCR 超出范围）
4. 不推断缺失的币种信息（若输入未标注币种，输出 `currency: null` 并降低置信度）
5. 不进行金额的加减乘除等运算

### 适用对象

- 需要从销售报表、订单记录、网页价格列表中提取金额的开发人员
- 需要批量清洗历史金额数据的数据分析人员
- 需要将非结构化金额文本转为 API 可消费 JSON 的自动化流程


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

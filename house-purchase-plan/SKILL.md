---
slug: house-purchase-plan
name: house-purchase-plan
displayName: 购房测算 月供税费 压力评估
description: 输入收入与房价，输出月供、税费、现金流压力与购房建议。
version: 1.1.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/house-purchase-plan
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["house-purchase-plan", "买房测算", "月供计算", "购房预算", "房贷方案对比"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# 购房测算 Skill 文档

## 一、能力边界速查卡

本 Skill 用于**购房前的量化测算与方案对比**，不涉及具体楼盘推荐、政策解读或法律意见。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| **贷款计算** | 等额本息/等额本金月供、总利息、本金构成 | 公积金与商贷组合贷的精确分摊（需用户提供比例） |
| **税费估算** | 契税、个税、增值税、中介费的**近似估算**（按常见税率） | 精确到区县的税率浮动、减免政策判定 |
| **能力评估** | 月供收入比、应急储备金覆盖月数、反向可承受房价 | 征信审核、银行批贷结果预测 |
| **方案对比** | 多房源横向对比、利率敏感性分析、提前还款模拟 | 房产升值/贬值预测、投资回报分析 |
| **输出形式** | 表格、文字报告、对比清单 | 生成法律效力的合同或证明文件 |

**适用对象**：首次购房者、换房改善者、房产投资者（仅用于现金流测算部分）。


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

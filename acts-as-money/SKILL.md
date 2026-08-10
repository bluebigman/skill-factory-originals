---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: acts-as-money
name: acts-as-money
displayName: 金额字段 货币换算
description: 将任意来源的金额数据标准化为货币对象，支持批量清洗与格式校验。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/acts-as-money
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["acts-as-money", "货币处理", "金额标准化", "money gem", "金额字段清洗", "货币换算", "金额格式化"]
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

# acts-as-money 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 核心能力清单

| 序号 | 能力项 | 说明 | 输入示例 | 输出示例 |
|------|--------|------|----------|----------|
| 1 | 金额数据标准化 | 将字符串、浮点数、整数等原始数据转换为统一的货币对象结构 | `"1,234.56"` | `{ amount: 1234.56, currency: "USD" }` |
| 2 | 货币单位识别 | 自动识别输入中的货币符号、代码（如 $、€、USD、CNY） | `"$99.99"` | `{ amount: 99.99, currency: "USD" }` |
| 3 | 批量 | 对数组/中的多行金额数据进行批量处理 | `["$10", "€20", "¥30"]` | 结构化货币对象数组 |
| 4 | 格式校验与纠错 | 检查金额格式合法性，对常见错误（如千分位错位）给出修正建议 | `"1,23,456.78"` | 警告 + 修正后的标准格式 |
| 5 | 自定义输出格式 | 支持按用户需求输出为 JSON、CSV、等不同结构 | 指定 `format: ""` | 对应格式的文本结果 |

### 1.2 不能做的事项

- 不执行实时汇率换算（仅识别货币单位，不进行汇率转换）
- 不处理非金额类数据（如日期、电话号码）
- 不保证输入数据的业务真实性（仅做格式与结构处理）
- 不自动修改原始数据源（输出为独立结果，不写回原文件）

### 1.3 适用对象

- 需要批量处理财务数据的运营人员
- 需要将金额字段导入数据库的开发人员
- 需要统一多币种报式的分析师
- 需要清洗历史遗留数据的数据工程师


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

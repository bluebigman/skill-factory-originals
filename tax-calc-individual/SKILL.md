---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: tax-calc-individual
name: tax-calc-individual
displayName: 个税精算 收入筹划 税后测算
description: 根据收入构成计算个税，输出税后收入与筹划建议。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/tax-calc-individual
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 税筹工坊
agent_created: true
trigger_words: ["个税计算", "个人所得税", "税后收入", "年终奖计税", "劳务报酬计税", "经营所得计税", "个税筹划"]
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

# 个税精算 收入筹划 税后测算

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 收入类型 | 工资薪金、年终奖（全年一次性奖金）、劳务报酬、经营所得（个体工商户/个人独资/合伙） | 股息红利、财产租赁、财产转让、偶然所得、稿酬（可扩展但当前版本不处理） |
| 扣除项 | 基本减除费用（5000元/月）、专项扣除（三险一金）、专项附加扣除（子女教育、继续教育、大病医疗、住房贷款利息、住房租金、赡养老人、3岁以下婴幼儿照护）、其他扣除（企业年金、商业健康险、税延养老保险） | 捐赠支出（限额扣除规则复杂，当前版本不处理）、境外所得抵免 |
| 计算能力 | 综合所得年度汇算、年终奖单独计税/并入综合所得对比、经营所得五级超额累进、劳务报酬预扣预缴 | 跨年度税收规划、股权激励计税、外籍人员特殊计税规则 |
| 输出能力 | 税后收入、应纳税额、有效税率、边际税率、筹划建议 | 税务申报表填写、法律意见出具 |

### 1.2 适用对象

- 需要估算个人年度税负的工薪族
- 有年终奖、劳务报酬等多源收入的自由职业者
- 个体工商户、个人独资企业经营者
- 需要快速对比"年终奖单独计税 vs 并入综合所得"的财务人员

### 1.3 关键参数速查

| 参数 | 数值 | 说明 |
|------|------|------|
| 基本减除费用 | 5000元/月（60000元/年） | 综合所得统一适用 |
| 综合所得税率 | 3% ~ 45%（7级超额累进） | 年度应纳税所得额分档 |
| 经营所得税率 | 5% ~ 35%（5级超额累进） | 年度应纳税所得额分档 |
| 劳务报酬预扣率 | 20% ~ 40%（3级） | 预扣预缴阶段适用 |
| 年终奖单独计税 | 按月换算后适用月度税率表 | 每年限用一次 |


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

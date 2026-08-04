---
slug: expense-reimburse
name: expense-reimburse
displayName: 报销单据 发票核验 归类制表
description: 整理报销单据，核验发票真伪，核对金额，归类并生成明细表。
version: 1.3.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/expense-reimburse
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: ExpenseFlow Studio
agent_created: true
trigger_words: 
  - "expense-reimburse"
  - "报销整理"
  - "发票核验"
  - "报销明细表"
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# 报销单据整理与核验 Skill

## 一、能力边界：一页纸速查卡

**我能做什么：**

| 能力项 | 说明 | 输入要求 |
|--------|------|----------|
| 发票真伪初查 | 根据发票代码、号码、金额等关键字段，判断是否符合常见发票规则，并提示需通过官方渠道复核 | 发票关键信息（代码、号码、金额、日期） |
| 金额核对 | 逐张比对发票金额与报销单填写金额，标记差异 | 报销单总金额 + 发票金额列表 |
| 报销类别归类 | 将费用归入差旅费、办公费、业务招待费、通讯费等常见类别 | 费用描述或商户名称 |
| 生成报销明细表 | 输出结构化 Markdown 表格，按类别汇总 | 整理后的单据信息 |

**我不能做什么：**

- ❌ 不能直接访问税务系统进行官方发票查验（需用户自行前往国家税务总局全国增值税发票查验平台）
- ❌ 不能处理 OCR 图像识别（需用户提供文本形式的发票信息）
- ❌ 不能代替财务人员做合规性最终判断（仅提供初筛建议）
- ❌ 不能处理非发票类凭证（如收据、白条，仅可标记提醒）

**适用对象：**

- 需要整理个人月度报销的员工
- 帮助同事汇总报销单的行政助理
- 需要快速初审报销材料的小团队负责人


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

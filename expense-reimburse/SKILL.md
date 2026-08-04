# 报销单据整理助手

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/expense-reimburse
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

## 一、能力边界速查卡

### 能做什么

| 能力项 | 说明 | 边界值 |
|--------|------|--------|
| 发票真伪初查 | 根据发票代码、号码、校验码等要素做格式合规性检查 | 仅限格式校验，不连接税务系统验真 |
| 金额核对 | 比对发票金额、报销单金额、计算逻辑一致性 | 支持小数两位，超出自动标记 |
| 报销类别归类 | 按费用性质划分至差旅、餐饮、办公、交通等类别 | 预设 8 个类别，自定义需人工确认 |
| 报销明细表生成 | 输出结构化 Markdown 表格，含汇总行 | 单次最多处理 50 张单据 |

### 不能做什么

| 事项 | 说明 |
|------|------|
| 不连接税务系统 | 无法做官方发票验真，仅做字段格式和规则校验 |
| 不替代财务审批 | 不判断是否可报销、不执行审批流 |
| 不识别图片 | 仅处理文本型数据，需用户提供结构化信息 |
| 不处理跨币种 | 仅支持人民币单币种，汇率换算需人工介入 |
| 不记忆历史数据 | 每次会话独立，不跨会话记录数据 |

### 适用对象

- 需要整理月度报销单据的职场人员
- 需将零散发票信息汇总成表的行政/财务助理
- 个人记账时需对消费票据做分类的用户


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

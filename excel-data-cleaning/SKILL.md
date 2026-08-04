# Excel 数据清洗工坊 (Excel Data Cleaning Workbench)

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/excel-data-cleaning
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

## 一、能力边界速查卡

### ✅ 能做什么

| 能力项 | 说明 | 关键参数 |
|--------|------|----------|
| **行级去重** | 按指定列组合识别重复行并删除 | `dedup_cols: ["订单号"]` 或 `dedup_cols: []`（全列去重） |
| **空格清理** | 去除字符串列首尾空白字符（含全角空格） | `strip_cols: ["客户名称", "地址"]` 或 `[]`（全列处理） |
| **格式统一** | 日期→`YYYY-MM-DD`；金额→去除千分位与货币符号；数字→统一小数位 | `date_cols`、`amount_cols`、`number_precision` |
| **异常值标记** | 3σ 离群检测 + 正则校验（邮箱/手机/身份证），命中值前缀 `[异常]` | `outlier_cols`、`validate_cols` |
| **多表合并** | 同簿多 Sheet 纵向堆叠；多文件按行/列拼接 | `merge_type: "sheet" / "row" / "col"` |
| **编码修复** | 自动识别 UTF-8 BOM、GBK 乱码并转码 | 自动，无需配置 |
| **清洗报告** | 生成 HTML 报告：行数变化、异常明细、操作日志、数据质量评分 | `report_path` |

### ❌ 不能做什么

- 不能处理 **50MB 以上** 或 **超 100 万行** 的单个文件（需拆分为多个批次）
- 不能自动识别业务语义（如"客户名称"是否指同一实体需人工确认）
- 不能修复逻辑性错误（如日期为 2023-02-30）
- 不能处理加密/密码保护的 Excel 文件

### 🎯 适用对象

- 电商运营：订单表去重、地址清洗
- 财务人员：金额格式统一、异常交易标记
- 数据分析师：多源数据合并前的预处理
- 行政人事：花名册去空格、证件号校验


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

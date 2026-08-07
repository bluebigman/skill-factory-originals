---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: expense-reimburse
name: expense-reimburse
displayName: 报销单据 发票核验 费用归类
description: 整理报销票据，核验发票真伪，归类费用并生成明细表。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/expense-reimburse
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 财务流程优化组
agent_created: true
trigger_words: ["报销整理", "发票核验", "报销单归类", "费用明细表", "票据整理", "贴票助手", "报销单整理"]
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

# 报销单据整理与发票核验 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| 票据整理 | 识别常见票据类型（增值税发票、出租车票、火车票、餐饮定额票等），按日期/类别分组 | 识别手写白条、无税务监制章的收据、模糊不清的扫描件 |
| 发票核验 | 根据发票代码、号码、开票日期、校验码等要素，提示真伪核验路径（税务官网/APP） | 直接访问税务系统完成真伪验证（需用户自行操作） |
| 金额归类 | 按费用类型（交通、餐饮、住宿、办公用品等）汇总金额，生成明细表 | 判断费用是否超标、是否符合公司内部报销政策 |
| 表单生成 | 输出结构化明细表（Markdown 表格或 CSV 格式） | 直接提交到企业 OA/财务系统（需人工导入） |

### 1.2 适用对象

- 需要整理个人月度报销单的职场人员
- 需要批量核验发票信息的小微企业财务助理
- 需要将纸质票据电子化归档的行政人员

### 1.3 输入输出规格

| 项目 | 规格 |
|------|------|
| 输入 | 票据照片/扫描件的文字描述、发票关键字段（代码、号码、金额、日期）、费用类别标签 |
| 输出 | 按费用类别归类的明细表（含发票核验状态标注）、待核验发票清单 |
| 处理量 | 单次建议不超过 50 张票据（超出建议分批处理） |


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

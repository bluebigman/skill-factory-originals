---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: stock-fund-report
name: stock-fund-report
displayName: 基金持仓透视 报表可视化 盈亏分析
description: 解析基金持仓数据，生成可视化报表与盈亏分析，辅助投资决策参考。
version: 1.2.2
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/stock-fund-report
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataViz Studio
agent_created: true
trigger_words: ["stock-fund-report", "基金报表", "持仓分析", "盈亏可视化", "基金数据透视"]
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

# 基金持仓报表生成与可视化 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 序号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 字段解析 | 从用户提供的文本或中提取基金代码、名称、市值、成本、盈亏、持仓比例等关键字段 |
| 2 | 数据处理 | 对持仓数据进行排序、汇总、占比计算、盈亏统计等规范化处理 |
| 3 | 报表生成 | 输出结构化报表，支持 Markdown 、CSV 格式及简单的文本可视化 |
| 4 | 置信度标注 | 对解析结果中不确定的字段标注 `[需核实:字段名]`，提示用户确认 |
| 5 | 错误诊断 | 识别输入格式问题，返回明确的错误码与修正指引 |

### 1.2 不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不提供投资建议 | 本技能仅做数据整理与展示，不包含买卖时机判断、收益预测等 |
| 2 | 不连接实时行情 | 不获取实时市场价格，所有数据以用户输入为准 |
| 3 | 不执行交易操作 | 不连接任何交易系统，不产生实际交易指令 |
| 4 | 不处理非结构化文本 | 需要相对规整的输入格式，纯自然语言描述需先转化为结构化数据 |

### 1.3 适用对象

- 个人投资者：整理自己的基金持仓，生成可视化报表
- 理财顾问：为客户生成持仓概览，辅助沟通
- 学习研究者：分析基金组合结构，进行数据透视练习


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: data-visual-report
name: data-visual-report
displayName: 数据洞察 图表报告 自动生成
description: 将表格数据自动转为带图表与结论的可视化分析报告
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/data-visual-report
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨研
agent_created: true
trigger_words: ["数据可视化", "图表报告", "趋势分析", "占比统计", "TopN排行", "数据洞察", "报表生成"]
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

# 数据洞察 · 图表报告自动生成 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入要求 |
|--------|------|----------|
| 趋势分析 | 识别时间序列数据的上升/下降/波动规律 | 至少 3 个时间点，数值型字段 |
| 占比统计 | 计算各分类在总体中的份额 | 分类字段 + 数值字段 |
| TopN 排行 | 按指定指标取前 N 名 | 任意维度字段 + 排序字段 |
| 图表生成 | 自动匹配折线图/柱状图/饼图 | 结构化表格数据（CSV/JSON/Excel 粘贴） |
| 结论提炼 | 基于数据特征输出自然语言洞察 | 数据量 ≥ 5 行，字段 ≥ 2 列 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 非表格数据 | 不接受纯文本、图片、音频输入 |
| 因果推断 | 只描述相关性，不推断业务因果 |
| 预测未来 | 不输出超出数据范围的预测值 |
| 数据清洗 | 不自动修正缺失值/异常值，仅标记 |
| 多表关联 | 仅处理单张二维表，不做跨表 JOIN |

### 1.3 适用对象

- 需要快速产出周报/月报的运营人员
- 需要数据佐证结论的产品经理
- 需要将实验数据可视化的研究人员
- 任何持有结构化表格但缺乏可视化技能的用户


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

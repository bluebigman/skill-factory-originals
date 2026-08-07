---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: annual-report-summary
name: annual-report-summary
displayName: 年报速读 财务透视 决策助手
description: 解析上市公司年报，提炼关键财务指标与投资决策参考信息。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/annual-report-summary
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FinSight Studio
agent_created: true
trigger_words: ["年报解读", "财报分析", "年度报告摘要", "财务数据提炼", "投资决策支持", "年报速览", "财务体检", "年报要点"]
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

# 年报速读 · 财务透视 · 决策助手

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 编号 | 能力项 | 说明 | 输出示例 |
|------|--------|------|----------|
| C1 | 年报文本解析 | 从 PDF/文本中提取财务章节 | 资产负债表、利润表、现金流量表关键行项目 |
| C2 | 关键比率计算 | 基于原始数据计算财务比率 | 毛利率、净利率、ROE、资产负债率、流动比率 |
| C3 | 趋势对比 | 与上年同期数据对比 | 营收同比、净利润同比、经营现金流同比 |
| C4 | 结构化摘要 | 按固定模板输出摘要 | 财务概览、盈利质量、偿债能力、运营效率四段式 |
| C5 | 风险信号标注 | 识别异常波动或警示项 | 应收账款激增、存货积压、商誉占比过高 |
| C6 | 决策参考建议 | 基于数据给出中性参考 | 关注点清单、需进一步核实事项 |

### 1.2 不能做什么

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不提供投资建议 | 不给出"买入/卖出/持有"结论，不预测股价走势 |
| L2 | 不保证数据完整性 | 若原始文件缺失章节或数据模糊，输出占位符而非猜测 |
| L3 | 不替代专业审计 | 不验证年报数据真实性，仅做文本层面的提炼与计算 |
| L4 | 不支持非结构化附件 | 仅处理可读取的文本/PDF，不解析图片中的表格（除非可OCR） |
| L5 | 不跨市场适配 | 默认适用A股年报格式；港股/美股字段映射需额外说明 |

### 1.3 适用对象

- 个人投资者：快速了解持仓或关注标的的财务概况
- 财务分析师：作为初步筛选工具，定位需深挖的科目
- 财经内容创作者：生成年报解读素材框架
- 学生研究者：学习财务分析框架的参考样例


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

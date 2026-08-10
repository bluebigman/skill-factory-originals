---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: annual-report-summary
name: annual-report-summary
displayName: 年报速读 财报解析 投资要点
description: 解析上市公司年报，提炼营收利润、现金流、负债与分红要点，输出投资摘要。
version: 1.0.3
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/annual-report-summary
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FinSight Studio
agent_created: true
trigger_words: ["年报解读", "财报分析", "投资要点", "年度报告摘要", "财务数据提取", "上市公司年报"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# 年报速读 · 财报解析 · 投资要点

## 一、能力边界：一页纸速查卡

### 1.1 能做（核心能力清单）

| 序号 | 能力项 | 说明 | 输出物 |
|------|--------|------|--------|
| 1 | 年报文件解析 | 支持 PDF/TXT/HTML 格式的年报全文或摘要，提取关键财务数据 | 结构化数据表 |
| 2 | 关键信息识别 | 自动定位营收、净利润、经营现金流、资产负债率、分红方案等核心字段 | 字段清单 |
| 3 | 结构化输出 | 按约定模板生成 Markdown/JSON 格式的投资要点摘要 | 摘要文档 |
| 4 | 置信度标注 | 对提取的每项数据标注置信度等级（高/中/低） | 置信度标签 |
| 5 | 批量处理 | 支持多份年报依次处理，输出汇总对比表 | 批量汇总表 |

### 1.2 不能做（明确边界）

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不提供投资建议 | 仅做数据整理与事实呈现，不判断买卖时机 |
| 2 | 不保证数据完整性 | 年报原文缺失或模糊时，输出占位符而非推测值 |
| 3 | 不处理非结构化 | 扫描版年报中的需先经 OCR 转换 |
| 4 | 不进行跨期对比分析 | 仅处理当前输入的年报，不做多年度趋势判断 |
| 5 | 不识别非财务信息 | 管理层讨论、行业分析等文字内容不纳入结构化输出 |

### 1.3 适用对象

- 个人投资者：快速了解目标公司年度经营状况
- 财务分析师：作为初步筛选工具，辅助深度研究
- 财经编辑：生成年报新闻稿的数据底稿
- 学生研究者：学习上市公司财务结构的基础参考


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

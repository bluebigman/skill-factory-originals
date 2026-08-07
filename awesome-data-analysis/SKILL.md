---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: awesome-data-analysis
name: awesome-data-analysis
displayName: 数据分析 可视化 洞察提炼
description: 将用户提供的原始数据转化为结构化洞察，支持可视化与批量处理。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/awesome-data-analysis
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataCraft Studio
agent_created: true
trigger_words: ["数据可视化", "数据分析", "awesome-data-analysis", "数据洞察", "图表生成"]
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

# awesome-data-analysis 技能文档

## 一、能力边界速查卡

### 1.1 核心能力清单

| 序号 | 能力项 | 说明 | 输入示例 | 输出示例 |
|------|--------|------|----------|----------|
| 1 | 数据解析 | 从 CSV/JSON/Excel/URL 中提取结构化数据 | `data.csv` 文件 | 标准化表格数据 |
| 2 | 关键信息识别 | 自动检测字段类型、数值范围、缺失值 | 含 `date`、`amount` 字段的数据集 | 字段类型标注与统计摘要 |
| 3 | 可视化生成 | 输出图表配置或图像文件（PNG/SVG） | 时间序列数据 | 折线图配置 JSON |
| 4 | 置信度标注 | 对推断结果附加可信度等级 | 缺失 30% 的数据集 | `confidence: 0.7` |
| 5 | 批量处理 | 支持多文件/多 URL 并行处理 | 10 个 CSV 文件路径列表 | 合并后的分析报告 |

### 1.2 能力边界声明

**能做：**
- 处理大小不超过 50MB 的本地文件
- 识别常见编码（UTF-8/GBK/ASCII）
- 输出 Markdown 表格、JSON、CSV 三种格式
- 对时间序列、分类数据、数值分布三类数据生成可视化建议

**不能做：**
- 无法访问需要登录认证的私有数据源
- 不执行实时数据抓取（仅处理用户主动提供的 URL）
- 不进行预测性建模（如回归预测、分类模型训练）
- 不生成交互式仪表盘（仅静态图表配置）

**适用对象：**
- 需要快速理解数据结构的业务分析师
- 需要生成图表配置的前端开发者
- 需要批量处理多个数据文件的数据运营人员


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

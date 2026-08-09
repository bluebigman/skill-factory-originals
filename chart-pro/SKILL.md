---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: chart-pro
name: chart-pro
displayName: 图表全流程 识别整理 生成校验
description: 图表识别、整理、生成与校验的一站式处理技能，输出可直接使用的图表文件。
version: 1.0.1
rules_version: cpr-20260809-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/chart-pro
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: ChartCraft Studio
agent_created: true
trigger_words: ["图表", "chart", "数据可视化", "图表生成", "图表整理", "图表校验"]
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

# chart-pro 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力模块 | 具体说明 | 输入示例 | 输出示例 |
|---------|---------|---------|---------|
| **图表识别** | 从图片、PDF、网页中识别图表类型、数据结构和坐标轴信息 | 一张柱状图截图 | 图表类型、数据表、标题、坐标轴说明 |
| **图表整理** | 清洗、标准化、合并多源图表数据，统一格式 | 多份格式不一的Excel图表数据 | 标准化后的CSV/JSON数据文件 |
| **图表生成** | 根据数据自动生成指定类型的图表（柱状、折线、饼图、散点、热力图等） | 数据表 + 图表类型要求 | 可直接使用的SVG/PNG/HTML图表文件 |
| **图表校验** | 检查图表数据准确性、视觉规范性和可读性 | 生成的图表文件 | 校验报告 + 修正建议 |

### 1.2 不能做什么

- ❌ 不能从模糊图片中还原高精度原始数据（只能估算）
- ❌ 不能生成3D交互式动态图表（仅支持静态图表）
- ❌ 不能处理超过10万行的大数据集（性能限制）
- ❌ 不能自动判断业务场景的图表选择是否合理（需用户确认）
- ❌ 不能生成包含敏感信息的图表（如个人隐私数据）

### 1.3 适用对象

- **数据分析师**：快速将原始数据转化为可视化图表
- **产品经理**：从竞品截图或用户反馈中提取图表信息
- **学生/教师**：制作课程报告、论文中的图表
- **运营人员**：将运营数据整理为周报/月报图表
- **开发者**：需要快速生成图表代码或静态资源


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

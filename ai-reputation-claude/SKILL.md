---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ai-reputation-claude
name: ai-reputation-claude
displayName: 口碑洞察 舆情评分 竞品对标
description: 解析评论数据，输出品牌声誉评分与竞品对比报告。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ai-reputation-claude
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingNan
agent_created: true
trigger_words: ["口碑分析","声誉管理","舆情监控","评论分析","竞品对标","品牌评分"]
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

# AI 声誉管理助手（口碑洞察）

## 一、能力边界速查卡

本 Skill 面向需要处理用户评论、舆情数据、品牌反馈的运营人员、市场分析师与产品经理。它帮助你将零散的文本数据转化为结构化、可比较的声誉评估结果。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入 | 用户粘贴的评论文本、CSV/Excel 文件路径、公开评论 URL | 无法直接抓取需登录验证的私有平台数据 |
| 分析 | 提取评论中的情感倾向、高频主题、关键事件 | 不进行深度语义推理或复杂因果推断 |
| 输出 | 生成结构化评分表、竞品对比矩阵、趋势摘要 | 不输出营销文案或公关建议 |
| 批量 | 支持多来源数据合并处理 | 单次处理超过 500 条评论时需分批 |
| 扩展 | 接受自定义评分权重与输出模板 | 不自动调整算法逻辑 |

**适用对象**：需要快速了解品牌舆论现状、定期追踪竞品动态、或为汇报准备数据支撑的职场人士。


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

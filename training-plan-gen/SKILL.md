---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: training-plan-gen
name: training-plan-gen
displayName: 健身计划定制 目标拆解 动作编排
description: 依据健身目标、时长与器械条件，生成结构化训练与饮食方案。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/training-plan-gen
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowState Studio
agent_created: true
trigger_words: ["训练计划", "健身计划", "减脂", "增肌", "塑形", " workout plan", "exercise routine"]
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

# 健身计划定制 Skill 文档

## 一、能力边界：一页纸速查卡

本 Skill 将用户的健身诉求（目标、可用时间、器械条件）转化为一份可执行的训练与饮食参考方案。它不替代教练面诊，也不做医学评估。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 目标解析 | 识别减脂、增肌、塑形三类核心目标，并区分主次目标 | 不处理康复训练、术后恢复、孕期训练等医疗场景 |
| 时间规划 | 根据每周可用天数与单次时长，编排训练频率与动作数量 | 不承诺任何时间内的体型变化速度 |
| 器械适配 | 区分自由重量、固定器械、自重训练、弹力带/小工具 | 不假设用户拥有特定品牌或型号的器械 |
| 动作编排 | 按肌群/动作模式（推、拉、蹲、 hinge、核心）分配动作 | 不生成需要专业保护或高难度技巧的动作（如抓举、倒立撑） |
| 饮食建议 | 给出蛋白质、碳水、脂肪的宏观比例参考与食物示例 | 不计算精确卡路里，不提供针对过敏原或疾病的饮食方案 |
| 输出格式 | 生成 Markdown 表格与结构化清单 | 不生成图片、视频或交互式训练动画 |

**适用对象**：有明确训练目标、能描述自身时间与器械条件的普通健身爱好者。不适用于专业运动员周期化训练设计。


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

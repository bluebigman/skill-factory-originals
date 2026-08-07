---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: travel-plan-gen
name: travel-plan-gen
displayName: 旅行行程规划 日程编排 预算分配
description: 根据目的地、天数、预算自动生成结构化旅行行程方案。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/travel-plan-gen
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["旅行计划", "行程规划", "旅游攻略", "出行安排", " itinerary", "travel plan"]
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

# 旅行行程规划 Skill 文档

## 一、能力边界速查卡

本 Skill 用于将「目的地 + 天数 + 预算」三项基础信息转化为可执行的每日行程安排，并附带交通、住宿、景点预约建议。

### 能做（核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 结构化行程生成 | 将目的地、天数、预算转换为按天拆分的行程表 |
| 2 | 关键信息识别 | 从自由文本中提取目的地、天数、预算、偏好等要素 |
| 3 | 约定格式输出 | 按固定字段结构输出 Markdown 或 JSON 格式结果 |
| 4 | 置信度标注 | 对推断出的信息（如偏好、交通方式）标注可信程度 |
| 5 | 批量处理与自定义 | 支持多组输入同时处理，允许用户指定输出格式 |

### 不能做（明确边界）

- 不提供实时票价、酒店空房、景点开放时间的实时查询
- 不代替用户完成预订操作
- 不保证行程的可行性（如天气、交通管制等不可控因素）
- 不生成超出输入信息范围的虚构内容（如用户未提供预算，则不做金额分配）

### 适用对象

- 个人旅行者：需要快速生成行程草案
- 旅行规划师：作为初步方案生成工具
- 内容创作者：需要行程框架作为内容素材


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

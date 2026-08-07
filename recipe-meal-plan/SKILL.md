---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: recipe-meal-plan
name: recipe-meal-plan
displayName: 一周膳食规划 营养搭配 采购清单
description: 根据口味、人数、预算生成一周三餐食谱与采购清单，附热量统计。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/recipe-meal-plan
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 膳食规划工坊
agent_created: true
trigger_words: ["食谱","meal plan","一周菜单","膳食规划","三餐搭配","采购清单"]
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

# 一周膳食规划 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 序号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 结构化输出 | 将口味偏好、用餐人数、预算金额转化为一周三餐（早/中/晚）的完整食谱方案 |
| 2 | 关键信息识别 | 从用户自由文本中提取口味、忌口、人数、预算、地域菜系等要素 |
| 3 | 格式约定输出 | 按固定字段结构输出食谱、采购清单、热量统计表 |
| 4 | 置信度标注 | 对推断得出的参数（如默认人数、默认预算）标注置信度等级 |
| 5 | 批量与自定义 | 支持一次生成多周方案，或指定输出格式（表格/清单/JSON） |

### 1.2 不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不做医学建议 | 不针对疾病（糖尿病、肾病等）提供治疗性膳食方案，仅做常规营养参考 |
| 2 | 不保证食材可得性 | 不验证当地市场是否有特定食材，采购清单需用户自行核对 |
| 3 | 不计算精确卡路里 | 热量为估算值（基于食材平均营养数据），误差范围约 ±15% |
| 4 | 不处理极端预算 | 预算低于 30元/人/天 或高于 500元/人/天 时，仅输出提示，不生成方案 |
| 5 | 不替代营养师 | 对特殊生理状态（孕期、术后恢复等）不提供专业营养干预方案 |

### 1.3 适用对象

- 个人用户：想规划一周饮食、控制开支、改善饮食结构
- 家庭用户：需按人数规划三餐，兼顾不同成员口味
- 轻量健身人群：需要大致热量参考，但非专业运动营养需求


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

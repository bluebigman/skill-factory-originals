---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ai-reputation-claude
name: ai-reputation-claude
displayName: 口碑洞察 舆情评分 竞品对标
description: 分析在线评论，量化品牌声誉，对标竞品，生成可执行洞察报告。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ai-reputation-claude
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨研
agent_created: true
trigger_words: ["ai-reputation-claude","口碑分析","声誉管理","舆情评分","竞品对标","评论洞察"]
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

# AI 口碑洞察与声誉管理助手（ai-reputation-claude）

## 一、能力边界速查卡（一页纸）

本 Skill 用于处理文本类口碑数据（评论、评分、社交提及），输出结构化分析结果。请先确认你的需求是否落在能力范围内。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入类型 | 用户粘贴的文本、上传的 CSV/TXT/JSON 文件、公开可访问的 URL 页面内容 | 需要登录的私有系统、动态渲染的 JS 页面、图片/音视频内容 |
| 分析功能 | 情感倾向识别、主题聚类、评分聚合、竞品对比、趋势摘要 | 因果归因推断、预测未来销量、识别虚假评论（仅能提示异常模式） |
| 输出格式 | Markdown 报告、JSON 结构化数据、CSV 表格 | 直接发布到任何平台、生成图表文件（仅能提供图表数据） |
| 处理规模 | 单次建议 10~500 条评论；超过 500 条需分批并提供汇总逻辑 | 实时流式数据处理、百万级语料训练 |
| 置信度 | 每条结论标注置信度（高/中/低） | 无数据支撑时编造数字或结论 |

**适用对象**：需要快速了解品牌/产品网络口碑的市场运营人员、产品经理、创业者、学术研究者。


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

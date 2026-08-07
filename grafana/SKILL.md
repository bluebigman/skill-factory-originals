---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: grafana
name: grafana
displayName: 数据可视化 观测分析 图表构建
description: 将多源数据转化为可视化图表与观测分析结果，辅助决策。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/grafana
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingDataWorks
agent_created: true
trigger_words: ["grafana", "数据可视化", "观测分析", "图表构建", "dashboard", "指标看板"]
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

# Grafana 数据可视化与观测分析 Skill

## 一、能力边界速查卡

本 Skill 面向需要将原始数据转化为可视化看板或观测分析结论的用户，包括数据分析师、运维工程师、产品经理等角色。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 数据输入 | 接受 CSV/JSON/URL 指向的数据源、用户粘贴的文本数据 | 不直接连接真实 Grafana 实例拉取数据 |
| 图表设计 | 根据数据特征推荐图表类型（折线、柱状、饼图、热力图等） | 不生成可执行的前端代码文件 |
| 指标分析 | 识别趋势、异常点、对比关系，给出结构化解读 | 不做预测性建模或因果推断 |
| 输出格式 | 生成 Markdown 表格、结构化 JSON 摘要、图表配置建议 | 不生成二进制文件或图片 |
| 批量处理 | 支持多指标、多时间段的批量分析请求 | 不支持流式数据的实时处理 |

**适用对象**：需要快速理解数据分布、构建可视化方案、撰写观测报告的用户。不适用于需要直接操作 Grafana API 或插件开发的场景。


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

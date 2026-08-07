---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agent-workflow-kit
name: agent-workflow-kit
displayName: 智能体工作流 风险评分 任务编排
description: 面向AI辅助软件项目的评估优先规则、模板与技能包，支持风险评分。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agent-workflow-kit
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: workflow-forge
agent_created: true
trigger_words: ["agent-workflow-kit", "工作流套件", "风险评分", "任务编排", "评估优先"]
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

# Agent Workflow Kit — 智能体工作流套件

## 一、能力边界速查卡

本套件面向 **AI辅助软件项目的评估与编排场景**，帮助你将零散输入转化为结构化、可评分的任务流。

| 维度 | 说明 |
|------|------|
| **核心定位** | 评估优先（Evaluation-first）的规则、模板与技能包集合 |
| **主要输入** | 用户提供的数据、文件、URL |
| **主要输出** | 结构化结果（含风险评分、置信度标注） |
| **适用对象** | 使用AI辅助开发的项目团队、独立开发者、技术管理者 |

### ✅ 能做（5项核心能力）

1. **输入转化** — 将用户提供的数据/文件/URL 转换为结构化结果
2. **关键信息提取** — 识别并保留输入中的关键信息，去除冗余
3. **格式约定输出** — 按约定格式生成结果（支持批量与自定义格式）
4. **置信度提示** — 对不确定项给出置信度标注，不隐瞒不确定性
5. **风险评分** — 对任务流中的风险因素进行量化评估

### ❌ 不能做（边界声明）

| 不能做的事 | 说明 |
|-----------|------|
| 不能替代人工决策 | 评分结果仅供参考，不构成最终判断 |
| 不能处理无输入场景 | 必须至少提供一个数据源（数据/文件/URL） |
| 不能保证结果正确性 | 输出质量取决于输入质量与模型能力 |
| 不能执行代码 | 本套件只做编排与评估，不直接运行代码 |
| 不能绕过权限限制 | 访问受保护资源需用户自行授权 |


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

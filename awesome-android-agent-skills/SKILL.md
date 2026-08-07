---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: awesome-android-agent-skills
name: awesome-android-agent-skills
displayName: Android技能导航 任务编排与执行
description: 面向Android智能体的技能检索、编排与执行辅助工具。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/awesome-android-agent-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["awesome android agent skills", "android技能", "技能编排", "android agent", "技能导航"]
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

# awesome-android-agent-skills 技能文档

## 一、能力边界：一页纸速查卡

本技能面向 **Android 智能体（Agent）开发者与使用者**，用于在 `awesome-android-agent-skills` 生态中快速定位、筛选、组合可复用的技能模块，并输出结构化的技能调用方案。

| 维度 | 说明 |
|------|------|
| **核心用途** | 将用户输入的技能需求（自然语言描述 / 技能名称 / 场景关键词）解析为结构化的技能匹配结果与执行建议 |
| **输入类型** | ① 自然语言需求描述 ② 技能名称或关键词列表 ③ 包含技能清单的 URL 或文件路径 |
| **输出类型** | Markdown 格式的技能匹配报告，包含：匹配技能列表、置信度评分、组合建议、前置依赖说明 |
| **处理上限** | 单次最多解析 20 个技能条目；超出部分截断并提示用户分批提交 |
| **批量模式** | 支持通过 `--batch` 参数传入 JSON 文件（格式见下文），一次处理多组需求 |

### 能做（5 项核心能力）

1. **需求解析**：从用户输入中提取技能相关的关键实体（技能名、版本号、平台要求、功能关键词）。
2. **技能匹配**：基于内置的 `awesome-android-agent-skills` 索引库，返回匹配度 Top 5 的技能条目。
3. **组合建议**：当单个技能无法覆盖需求时，推荐 2-3 个技能的串联组合方案。
4. **置信度标注**：每条匹配结果附带 0-1 的置信度分数，低于 0.6 时明确标注 `[需核实]`。
5. **格式转换**：支持将匹配结果导出为 JSON / Markdown / CSV 三种格式。

### 不能做（明确边界）

- ❌ 不执行任何 Android 代码或调用真实 API——本技能仅做信息检索与编排建议。
- ❌ 不保证匹配结果的绝对正确性——技能库持续更新，结果仅供参考。
- ❌ 不处理与 Android 技能无关的通用问题（如财务、医疗建议）。
- ❌ 不存储用户输入数据——所有处理均在会话内完成，不写入持久化存储。

### 适用对象

- **初级用户**：不知道有哪些技能可用，需要导航与推荐。
- **进阶用户**：有明确技能需求，需要快速比对多个候选技能。
- **开发者**：需要将技能组合嵌入自己的 Agent 工作流。


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

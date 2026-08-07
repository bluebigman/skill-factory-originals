---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: planning-with-files
name: planning-with-files
displayName: 文件规划 持久化任务管理
description: 基于文件的持久化规划，支持崩溃恢复与长任务跟踪
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/planning-with-files
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Ling
agent_created: true
trigger_words: ["planning with files", "文件规划", "持久化计划", "崩溃恢复", "任务跟踪", "markdown计划"]
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

# planning-with-files — 基于文件的持久化规划 Skill

## 一、能力边界（一页纸速查卡）

### ✅ 能做（5项核心能力）

| 编号 | 能力 | 说明 |
|------|------|------|
| 1 | 将用户提供的数据/文件/URL 转换为结构化结果 | 支持从多种输入源提取信息，生成统一的 Markdown 计划文档 |
| 2 | 识别并保留输入中的关键信息 | 自动提取任务目标、约束条件、时间节点、依赖关系等核心要素 |
| 3 | 按约定格式生成输出 | 输出遵循固定的 Markdown 模板，包含状态、进度、下一步行动等字段 |
| 4 | 对不确定项给出置信度提示 | 对无法确认的信息标注 `[需核实:字段名]` 占位符，不编造内容 |
| 5 | 支持批量处理和自定义格式 | 可一次处理多个输入文件/URL，并允许用户指定输出模板 |

### ❌ 不能做（明确边界）

| 编号 | 限制 | 说明 |
|------|------|------|
| 1 | 不执行实际任务 | 本 Skill 只负责规划与记录，不代替 agent 执行代码或操作 |
| 2 | 不自动修改用户文件 | 除非用户明确要求，否则不覆盖已有文件 |
| 3 | 不保证任务成功率 | 规划只是辅助工具，实际执行结果取决于 agent 与环境 |
| 4 | 不处理加密或二进制文件 | 仅支持纯文本、Markdown、JSON、CSV 等可读格式 |
| 5 | 不提供实时协作 | 文件是唯一的共享媒介，不支持多人同时编辑 |

### 🎯 适用对象

- 需要长时间运行（数小时至数天）的 AI 编码任务
- 需要跨会话恢复上下文的 agent 工作流
- 需要人工审查进度的项目管理场景
- 需要崩溃后快速恢复的自动化流水线


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

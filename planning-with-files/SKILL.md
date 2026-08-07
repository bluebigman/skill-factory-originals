---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: planning-with-files
name: planning-with-files
displayName: 文件规划 任务跟踪 持久化备忘
description: 基于文件的持久化规划，支持崩溃恢复与长任务跟踪
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/planning-with-files
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 独立技能工坊
agent_created: true
trigger_words: ["planning with files", "文件规划", "持久化计划", "崩溃恢复", "任务跟踪", "文件备忘", "断点续作"]
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

# 文件规划 Skill 使用指南

## 一、能力边界（一页纸速查卡）

### 本 Skill 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 创建持久化计划 | 将任务计划写入本地文件，而非内存 | 创建 `plan.md` 记录三阶段开发计划 |
| 崩溃恢复 | 从上次保存的文件状态继续执行 | 重启后读取 `plan.md` 恢复任务进度 |
| 长任务跟踪 | 跨会话维护任务状态、进度、备注 | 持续一周的数据清洗任务每日更新 |
| 多文件管理 | 支持主计划文件 + 子任务文件 | `plan.md` + `tasks/phase1.md` |
| 状态标记 | 用约定符号标记任务状态 | `[ ]` 待办 / `[x]` 完成 / `[~]` 进行中 |

### 本 Skill 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不替代项目管理软件 | 无甘特图、依赖关系自动计算、多人协作 |
| 不自动执行任务 | 仅记录与跟踪，不触发外部动作 |
| 不处理二进制文件 | 仅面向 Markdown / 纯文本文件 |
| 不加密敏感信息 | 文件为明文存储，注意权限控制 |

### 适用对象

- 需要跨会话跟踪任务的个人开发者
- 使用命令行或编辑器工作的技术用户
- 需要轻量级任务记录的场景（非企业级）


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

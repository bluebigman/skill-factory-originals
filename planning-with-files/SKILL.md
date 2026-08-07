---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: planning-with-files
name: planning-with-files
displayName: 文件规划 任务追踪 断点续作
description: 基于文件的持久化规划，支持崩溃恢复与长任务跟踪
version: 1.0.3
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/planning-with-files
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 独立技能工坊
agent_created: true
trigger_words: ["planning with files", "文件规划", "持久化计划", "崩溃恢复", "任务跟踪", "断点续作", "长任务管理"]
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

### 1.1 能做什么

| 能力项 | 说明 | 适用场景 |
|--------|------|----------|
| 计划落盘 | 将任务计划写入本地文件（Markdown/JSON） | 需要跨会话保留的计划 |
| 断点记录 | 记录任务执行到哪一步、下一步做什么 | 长任务中断后恢复 |
| 进度追踪 | 维护任务状态（待办/进行中/已完成/阻塞） | 多步骤项目跟踪 |
| 崩溃恢复 | 从上次保存的状态继续执行 | 会话意外中断、系统重启 |
| 变更留痕 | 每次修改计划时追加变更日志 | 需要审计轨迹的任务 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不替代项目管理工具 | 不提供甘特图、资源分配、多人协作 |
| 不自动执行任务 | 只记录计划，不调用外部工具执行任务 |
| 不处理二进制文件 | 仅支持纯文本格式（.md / .json / .txt） |
| 不跨设备同步 | 文件保存在本地，需自行同步 |

### 1.3 适用对象

- 需要跨会话跟踪的复杂任务（如软件开发、论文写作、数据分析）
- 经常中断需要恢复的工作流
- 偏好文件存储、不依赖云服务的用户


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

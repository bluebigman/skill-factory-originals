---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: planning-with-files
name: planning-with-files
displayName: 文件规划 持久任务 崩溃恢复
description: 基于文件的持久化规划，支持崩溃恢复与长任务跟踪
version: 1.0.4
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/planning-with-files
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 独立技能工坊
agent_created: true
trigger_words: ["planning with files", "文件规划", "持久化计划", "崩溃恢复", "任务跟踪", "断点续作", "计划存档"]
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

# 文件规划 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 计划持久化 | 将多步骤计划写入本地文件，非内存态 | 将 12 步迁移计划保存为 `plan.md` |
| 崩溃恢复 | 从文件读取上次进度，跳过已完成步骤 | 第 5 步崩溃，重启后从第 6 步继续 |
| 长任务跟踪 | 跨会话记录任务状态、完成度、备注 | 3 天周期的数据清洗任务每日更新 |
| 计划版本管理 | 每次修改保留时间戳副本 | `plan-20250101-1030.md` |
| 进度校验 | 对比文件记录与实际完成情况 | 标记已完成但实际缺失的步骤 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不替代任务执行 | 仅记录计划与进度，不自动执行任何步骤 |
| 不处理并发写入 | 同一计划文件同时被多个进程写入时，不保证一致性 |
| 不加密敏感内容 | 计划文件为明文，含密钥/密码需自行加密 |
| 不跨设备同步 | 文件存储于本地，不提供云同步能力 |
| 不解析非结构化文本 | 仅识别符合约定格式的标记（见 3.2 节） |

### 1.3 适用对象

- 需要跨会话/跨中断完成多步骤任务的开发者
- 需要审计任务执行历史的团队
- 在不可靠环境（如远程服务器、低功耗设备）中运行长任务的场景


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

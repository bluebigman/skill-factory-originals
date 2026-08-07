---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agent-loop-engine
name: agent-loop-engine
displayName: 循环引擎 代理编排 状态内核
description: 轻量级循环状态内核，管理代理团队持久目标、唤醒与交接。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agent-loop-engine
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林屿墨
agent_created: true
trigger_words: ["代理循环", "agent-loop", "循环引擎", "状态内核", "代理编排"]
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

# agent-loop-engine（循环引擎 · 代理编排 · 状态内核）

## 一、能力边界：一页纸速查卡

本 Skill 面向需要长期运行、多代理协作、状态可追溯的工程场景。它不是一个聊天机器人框架，而是一个**状态管理内核**，负责目标的持久化、唤醒条件的判定、待办事项的执行追踪以及交接过程的证据留存。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 目标管理 | 持久化存储长期目标，支持多目标优先级排序 | 自动生成目标（需用户或上游代理输入） |
| 唤醒机制 | 基于配额（时间/次数/资源阈值）自动判定是否唤醒代理 | 实际执行代理代码（仅输出唤醒指令） |
| 待办事项 | 记录可执行待办，标记状态（待办/进行中/已完成/阻塞） | 代替代理决策待办是否合理 |
| 证据日志 | 记录每次操作的关键证据（输入摘要、输出哈希、时间戳） | 篡改或删除历史日志（仅追加） |
| 交接验证 | 生成交接凭证，包含上下文摘要、未完成事项、风险提示 | 保证交接后对方一定成功（仅提供可验证信息） |

**适用对象**：需要多代理协作的开发者、AI 代理编排平台、自动化工作流设计者。

**不适用对象**：单次对话型应用、无状态请求-响应场景、需要实时人机交互的场景。


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

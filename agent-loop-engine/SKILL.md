---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agent-loop-engine
name: agent-loop-engine
displayName: 代理循环 状态内核 团队编排
description: 轻量级循环状态内核，管理代理团队持久目标、唤醒与交接。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agent-loop-engine
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["代理循环", "agent-loop", "循环引擎", "状态内核", "代理编排", "任务循环", "代理调度"]
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

# agent-loop-engine 技能文档

## 一、能力边界：一页纸速查卡

### 1.1 本 Skill 能做什么

| 能力项 | 说明 | 典型场景 |
|--------|------|----------|
| 持久目标管理 | 为代理团队维护长期目标状态，跨会话不丢失 | 多轮任务中保持团队方向一致 |
| 唤醒机制 | 根据条件或时间触发代理重新激活 | 定时检查任务进度、条件满足后继续执行 |
| 交接管理 | 在代理之间传递任务上下文与执行权 | 前端代理完成后将结果交给后端代理 |
| 循环状态追踪 | 记录每轮循环的状态变更、计数与历史 | 调试循环逻辑、观察状态流转 |
| 轻量级内核 | 不依赖重型框架，可直接嵌入现有代码 | 在脚本或小型服务中快速集成 |

### 1.2 本 Skill 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不提供 GUI | 仅提供编程接口与命令行工具，无图形界面 |
| 不负责代理内部逻辑 | 代理的具体决策、推理、工具调用由代理自身实现 |
| 不处理分布式一致性 | 单机内存态为主，跨进程需自行扩展持久化 |
| 不包含调度器 | 唤醒条件由调用方触发，本内核不主动跑定时任务 |
| 不保证任务成功 | 只保证状态流转正确，任务执行结果由代理负责 |

### 1.3 适用对象

- 正在构建多代理协作系统的开发者
- 需要为代理团队增加持久状态管理的中小型项目
- 希望快速验证代理循环逻辑的原型设计者


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

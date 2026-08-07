---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: pm-manager
name: pm-manager
displayName: 任务治理 优先级排序 修复决策
description: 将零散输入整理为结构化任务清单，辅助AI代理确定下一步修复动作。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/pm-manager
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["pm-manager", "pm manager", "项目管理", "任务治理", "优先级排序", "任务清单", "修复计划", "工作流编排"]
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

# pm-manager Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入示例 | 输出示例 |
|--------|------|----------|----------|
| 输入结构化 | 将自由文本、聊天记录、日志片段整理为统一格式的任务条目 | "登录页报错，用户反馈，还有那个支付超时也看看" | `[T-001] 登录页报错 | 优先级:高 | 状态:待处理` |
| 优先级排序 | 基于紧急度、影响面、依赖关系给出处理顺序建议 | 任务列表（含描述、影响范围） | 排序后的任务队列 + 排序理由 |
| 依赖分析 | 识别任务间的前置/后置关系 | 多个任务描述 | 依赖关系图（文本形式） |
| 下一步动作推荐 | 针对当前任务队列，给出"接下来做什么"的具体建议 | 任务队列 + 当前资源约束 | 明确的下一步动作 + 执行理由 |
| 状态追踪 | 维护任务生命周期（待处理→进行中→已完成→阻塞） | 任务ID + 状态变更指令 | 更新后的任务看板 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行实际修复 | 本 Skill 只做规划与排序，不直接修改代码、配置或数据 |
| 不替代人工决策 | 最终优先级裁决权在用户/代理手中，本 Skill 仅提供建议 |
| 不处理非文本输入 | 不支持图片、音频、视频等多媒体输入 |
| 不保证任务估算准确 | 时间估算仅基于经验公式，实际耗时受环境因素影响 |
| 不跨会话持久化 | 任务状态默认保存在当前会话内，如需持久化需用户自行存储 |

### 1.3 适用对象

- **AI 代理**：需要从杂乱输入中提取行动项的自动化系统
- **开发者**：面对多任务需要确定处理顺序的个人或团队
- **运维人员**：需要从告警信息中筛选高优问题的值班人员
- **产品经理**：需要将用户反馈整理为可执行需求清单


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

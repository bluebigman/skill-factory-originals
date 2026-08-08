---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: andrej-karpathy-skills
name: andrej-karpathy-skills
displayName: 编码协作 行为规范 提示词优化
description: 基于Karpathy观察的LLM编码缺陷，规范Claude Code协作行为，提升代码质量。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/andrej-karpathy-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["andrej-karpathy-skills", "karpathy编码规范", "claude-code行为优化", "llm编码陷阱", "AI协作开发规范"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# 编码协作行为规范 Skill 文档

## 一、能力边界：一页纸速查卡

### 1.1 本 Skill 能做什么

| 序号 | 能力项 | 具体说明 |
|------|--------|----------|
| 1 | 行为规范注入 | 将 Karpathy 观察到的 LLM 编码常见缺陷转化为可执行的协作规则，注入到 Claude Code 的上下文中 |
| 2 | 缺陷模式识别 | 识别代码生成过程中的 12 类高频缺陷模式（如过早优化、过度工程、忽略边界条件等） |
| 3 | 代码审查辅助 | 在代码审查阶段提供结构化检查清单，帮助发现潜在问题 |
| 4 | 提示词优化 | 根据 Karpathy 的观察，优化与 LLM 协作时的提示词策略，减少无效交互 |
| 5 | 工作流约束 | 为 Claude Code 设置明确的行为边界，防止其偏离用户真实意图 |

### 1.2 本 Skill 不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不替代代码审查工具 | 不执行静态分析、不检查语法错误、不运行测试 |
| 2 | 不保证代码质量 | 不承诺生成的代码无缺陷、无漏洞、性能最优 |
| 3 | 不覆盖所有场景 | 仅针对 Karpathy 观察到的典型缺陷模式，非通用编码规范 |
| 4 | 不自动修改代码 | 仅提供规则和建议，不直接修改用户的代码文件 |
| 5 | 不处理非编码任务 | 不适用于文档撰写、数据分析、设计等非编码场景 |

### 1.3 适用对象

- **适用**：使用 Claude Code 进行日常编码开发的开发者；希望减少 LLM 协作中常见错误的团队；对代码质量有较高要求的个人开发者。
- **不适用**：不使用 Claude Code 的用户；纯非编码场景；需要自动化代码修改的场景。


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

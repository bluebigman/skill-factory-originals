---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agencycli
name: agencycli
displayName: 多智能体协作 任务编排 命令行调度
description: 用Markdown+YAML定义角色与任务，命令行驱动AI智能体团队自主协作。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agencycli
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Ling Xiao
agent_created: true
trigger_words: ["agencycli", "智能体团队", "AI代理编排", "自主协作", "多智能体调度", "角色编排", "任务分派", "协作流程"]
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

# agencycli — 多智能体协作与任务编排命令行工具

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 角色定义 | 通过 YAML 文件定义 AI 角色的身份、职责、行为准则 | `roles/analyst.yaml` |
| 技能挂载 | 为角色绑定特定技能（Skill），限定其能力范围 | `skills: [data_analysis, report_writing]` |
| 任务编排 | 用 Markdown 编写任务描述，指定由哪个角色执行 | `tasks/task-001.md` |
| 团队协作 | 多个角色按顺序或并行执行任务，自动传递上下文 | 分析师产出数据 → 文案撰写报告 |
| 流程驱动 | 通过配置文件定义协作流程（顺序、分支、合并） | `pipeline.yaml` |
| 自检与版本 | 内置自检命令和版本查询 | `agencycli --selftest` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行外部 API 调用 | 工具本身不直接调用第三方服务（如 OpenAI API），需由宿主环境提供 |
| 不替代人工决策 | 角色输出结果需人工审核，工具不提供自动批准机制 |
| 不支持实时交互 | 所有任务通过文件定义，不支持命令行交互式对话 |
| 不处理非结构化输入 | 任务描述必须遵循 Markdown 规范，角色定义必须遵循 YAML 规范 |

### 1.3 适用对象

- **AI 应用开发者**：需要快速搭建多智能体协作原型的团队
- **自动化流程设计者**：需要将复杂任务拆解为多个 AI 角色协作的工程师
- **技术评估人员**：评估多智能体编排方案可行性的架构师


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

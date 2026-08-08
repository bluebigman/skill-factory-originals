---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agent-orchestration-coordinator
name: agent-orchestration-coordinator
displayName: 多智能体协作调度中枢
description: 协调多个AI代理分工协作，管理任务分配、进度追踪与结果整合。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agent-orchestration-coordinator
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["agent-orchestration-coordinator", "多代理协调", "任务编排", "协作调度", "工作流协调"]
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

# 多智能体协作调度中枢（Agent Orchestration Coordinator）

## 一、能力边界速查卡

本 Skill 面向需要将复杂任务拆解为多个子任务、分派给不同 AI Agent 并行或串行执行，并统一回收结果的场景。

| 维度 | 说明 |
|------|------|
| **核心用途** | 将用户提交的复杂目标拆解为可执行子任务，分派给多个 Agent，跟踪执行进度，汇总并校验最终结果 |
| **输入类型** | 自然语言任务描述、结构化任务清单（JSON/YAML）、包含任务列表的文件路径或 URL |
| **输出类型** | 结构化任务编排方案（JSON）、各 Agent 执行状态报告、汇总后的最终结果（Markdown/JSON） |
| **支持规模** | 单次编排 2~20 个子任务；超过 20 个建议分批处理 |
| **执行模式** | 串行（依赖型任务链）、并行（独立任务组）、混合（阶段式并行+串行） |

### ✅ 能做的事情

1. 解析用户提供的任务描述（自然语言或结构化数据），提取目标、约束条件和优先级。
2. 将复杂目标拆解为粒度合适的子任务，并标注每个子任务的输入依赖和输出要求。
3. 为每个子任务推荐合适的 Agent 角色（如：分析型、生成型、审查型、数据提取型）。
4. 生成任务编排方案（DAG 结构），明确各任务的执行顺序和并行关系。
5. 跟踪各 Agent 的执行状态（待执行/执行中/已完成/失败），并输出进度报告。
6. 汇总各 Agent 的产出，进行一致性校验（字段完整性、格式合规性、逻辑冲突检测）。
7. 对不确定的信息或缺失字段，显式标注 `[需核实:字段名]`，不进行臆测填充。

### ❌ 不能做的事情

1. 不能直接调用或启动任何外部 AI Agent 服务——本 Skill 仅生成编排方案和协调指令，实际执行需由宿主平台完成。
2. 不能保证某个 Agent 的输出一定正确——仅能通过交叉校验降低错误概率。
3. 不能处理未提供明确目标或输入数据的任务——缺少必要信息时，会返回错误码 `E_INSUFFICIENT_INPUT`。
4. 不能执行实时通信或推送通知——进度跟踪基于轮询式状态查询。
5. 不能处理超过 20 个子任务的单次编排——超出时建议拆分。

### 👥 适用对象

| 用户类型 | 适用场景 |
|----------|----------|
| 开发者 | 构建多 Agent 协作流水线，需要标准化编排协议 |
| 运维人员 | 监控多个自动化任务的执行状态与结果汇总 |
| 业务分析师 | 将复杂业务问题拆解为多个分析步骤，分派给不同分析 Agent |
| 技术管理者 | 评估多 Agent 协作方案的可行性与资源分配 |


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agent-orchestration-coordinator
name: agent-orchestration-coordinator
displayName: 多智能体协作调度中枢
description: 协调多个AI代理分工协作，跟踪任务进度并汇总结果，适用于复杂工作流编排。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agent-orchestration-coordinator
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingFlow Studio
agent_created: true
trigger_words: ["agent-orchestration-coordinator", "多智能体协作", "任务编排", "工作流协调", "agent调度", "任务分配与汇总"]
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

本 Skill 面向需要将复杂任务拆解为多个子任务、分派给不同 AI Agent 并行处理，并最终归拢结果的场景。它本身不执行具体业务逻辑，而是充当"调度中枢"的角色。

| 维度 | 说明 |
|------|------|
| **核心定位** | 任务分解 → 代理分配 → 进度追踪 → 结果整合 |
| **输入类型** | 用户提供的任务描述、数据文件（CSV/JSON/TXT）、URL 列表 |
| **输出格式** | 结构化 JSON 报告（含任务状态、代理输出、置信度标注） |
| **适用对象** | 需要多步骤处理的复杂任务、需要并行调研的课题、需要多角色评审的内容生产 |

### ✅ 能做（5 项核心能力）

1. **任务结构化拆解**：将用户描述的自然语言任务，拆解为可独立执行的子任务清单，并为每个子任务标注依赖关系（无依赖的任务可并行）。
2. **代理角色匹配**：根据子任务类型（如检索、分析、写作、审查），推荐合适的代理角色或工具类型，并给出匹配理由。
3. **进度状态跟踪**：为每个子任务维护状态机（待分配 → 执行中 → 已完成 → 失败），支持中途查询整体进度。
4. **结果汇总与冲突消解**：收集各代理返回的结果，按预设模板合并；若多个代理对同一问题给出矛盾结论，在输出中并列展示并标注差异。
5. **置信度标注与人工复核建议**：对每个汇总结果标注置信度（高/中/低），置信度为"低"的条目自动标记 `[需核实:字段名]`，提示用户介入确认。

### ❌ 不能做（明确边界）

- 不执行具体的领域推理（如法律条文分析、代码编译运行）——这些由下游代理完成。
- 不保证所有代理任务必然成功——网络超时、上游 API 限流等外部因素不在控制范围内。
- 不自动修改用户原始数据文件——所有输出均为新生成的结果文件。
- 不支持实时流式输出——任务完成后一次性返回完整报告。
- 不处理非文本输入（如图片内容识别）——如需处理图片，请先由其他工具转换为文本描述。


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

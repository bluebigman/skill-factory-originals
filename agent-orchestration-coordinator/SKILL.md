---
> 本内容由 AI 生成，仅供学习参考（《人工智能生成合成内容标识办法》显式标识）。
<!-- ai-generated-notice -->
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

## 前置条件

- Python 3.9+（脚本依赖标准库，无需联网即可运行自检）
- 已获取待处理的输入文件，并对其拥有合法使用权
- 建议先在样本数据上试运行，确认输出符合预期后再批量处理

## 执行步骤

1. **准备输入**：将待处理文件放入同一目录，确认命名规范一致。
2. **试运行**：先用单个样本执行，核对输出字段与格式。
3. **批量执行**：确认无误后对全量数据执行，并保留原始文件备份。
4. **校验结果**：抽查输出条目，核对关键字段与源数据一致。

## 输出

- 结构化结果文件（默认与输入同目录，带 `_out` 后缀），原始文件不被改写
- 控制台摘要：处理总数、成功数、跳过数、失败数
- 失败明细清单，含文件名与失败原因，便于定向重跑

## 异常处理

| 异常情况 | 表现 | 处理方式 |
|---|---|---|
| 输入文件不存在 | 提示路径错误并退出 | 核对路径，使用绝对路径重试 |
| 文件格式不符 | 该条跳过并计入失败明细 | 转换为受支持格式后重跑该条 |
| 权限不足 | 写入失败 | 更换输出目录或提升目录写权限 |
| 单条数据异常 | 跳过该条，继续处理其余 | 处理结束后查看失败明细定向重跑 |

失败处理原则：**单条失败不中断整批**，全部异常汇总到失败明细，支持只重跑失败项。

## 稳定性保障

- **超时控制**：单条处理设置上限，超时自动跳过并记入失败明细，避免整批卡死。
- **重试策略**：可恢复类错误（临时占用、瞬时 IO 失败）自动重试 3 次，间隔递增。
- **降级方案**：高级解析失败时自动回退到基础解析模式，保证有可用输出而非直接报错。
- **幂等性**：重复执行同一批输入结果一致，不会产生重复追加。

## FAQ 与反模式

**Q：可以直接对原始文件覆盖写入吗？**
A：不建议。默认输出到独立文件，保留原始数据是可回溯的前提。

**Q：处理到一半失败了怎么办？**
A：已完成部分的输出有效，查看失败明细后只重跑失败项即可，无需整批重来。

**反模式 ①**：不做试运行直接批量处理全量数据 —— 参数配错会一次性污染全部输出。

**反模式 ②**：忽略失败明细只看成功数 —— 静默跳过的条目会造成数据缺口。

**反模式 ③**：把工具输出直接作为最终结论 —— 关键字段务必人工抽检。

## 安全声明

- 全流程本地执行，不上传任何用户数据到第三方服务。
- 不读取与任务无关的目录，不写入系统目录。
- 处理含个人信息的数据时，请自行遵守《个人信息保护法》等相关法规。
- 本 Skill 代码由 AI 辅助生成并经自检验证，以 MIT 协议开源，使用者自负使用后果。

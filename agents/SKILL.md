---
slug: agents
name: 多智能体协作框架
displayName: 任务拆解 多角色协同 结果整合
description: 编排多个AI Agent分工协作，完成复杂任务并输出结构化结果
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingFlow Studio
agent_created: true
trigger_words: ["多智能体", "Agent协作", "任务编排", "分工协同", "多角色协作", "智能体调度"]

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

# 多智能体协作框架 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 典型应用场景 |
|--------|------|-------------|
| 任务拆解 | 将复杂任务按依赖关系拆分为多个子任务 | 市场调研报告、竞品分析、项目规划 |
| 角色分配 | 为每个子任务分配专职Agent角色 | 数据分析师、文案撰写、代码审查 |
| 流程编排 | 定义Agent之间的执行顺序与数据传递关系 | 数据采集→清洗→分析→可视化 |
| 结果整合 | 将各Agent输出合并为统一格式的结构化结果 | 周报汇总、多维度评估报告 |
| 状态追踪 | 监控每个Agent的执行进度与状态 | 长耗时任务进度查看、异常定位 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行外部API调用 | 本框架仅负责编排与调度，不直接发起网络请求 |
| 不处理实时流式数据 | 面向静态输入或分批输入的任务场景 |
| 不保证Agent输出质量 | 各Agent的生成质量取决于其底层模型能力 |
| 不支持动态修改任务图 | 任务图在启动前需确定，运行中不可变更 |

### 1.3 适用对象

- 需要将复杂任务拆解为多个独立步骤的开发者
- 需要多角色视角分析同一问题的研究场景
- 需要并行处理多个独立子任务的批处理场景
- 需要将多源输出整合为统一格式的报表场景


## 许可证（License）

```text
MIT License

Copyright (c) {year} {holder}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

```
<!-- professional-license-embedded -->

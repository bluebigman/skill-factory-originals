---
slug: agents
name: 多智能体协作框架
displayName: 任务编排 多角色协同 结构化产出
description: 编排多个AI Agent分工协作，完成复杂任务并输出结构化结果
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 协同流工作室
agent_created: true
trigger_words: ["多智能体", "Agent协作", "任务编排", "分工协同", "多角色协作", "智能体调度", "协作流程"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# 多智能体协作框架（Skill 文档）

## 一、能力边界：一页纸速查卡

本 Skill 用于将复杂任务拆解为多个 AI Agent 的分工协作流程，并按依赖关系执行后输出结构化结果。

### ✅ 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 任务拆解 | 将输入任务自动拆分为 2~5 个子任务 | "分析新能源汽车市场" → 拆为数据收集、竞品分析、趋势研判 |
| 角色分配 | 为每个子任务分配独立 Agent 角色 | 研究员 Agent、分析师 Agent、撰稿 Agent |
| 依赖编排 | 按先后依赖或并行关系执行各 Agent | Agent B 依赖 Agent A 的输出作为输入 |
| 结构化输出 | 汇总各 Agent 结果为统一格式报告 | 输出含市场规模、竞争格局、趋势预测的 Markdown 报告 |
| 置信度标记 | 对不确定信息标注 [需核实:字段]，不编造 | 数据缺失时输出 [需核实:2024年市场份额] |

### ❌ 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行外部实时调用 | 不主动联网、不调用 API、不访问本地文件（除非宿主环境提供） |
| 不保证数据时效性 | 训练数据存在截止时间，过时信息需用户自行核实 |
| 不替代专业决策 | 输出仅供参考，不构成投资、法律、医疗等专业建议 |
| 不处理超大规模拆分 | 子任务超过 5 个时需用户手动合并或分层 |

### 👥 适用对象

- 需要快速产出结构化调研报告的运营/产品/市场人员
- 需要将复杂问题分解为多步骤处理的 AI 工具使用者
- 希望了解多 Agent 协作模式的技术爱好者

---

## 二、触发方式：场景映射表

当你的输入包含以下关键词或意图时，本 Skill 将被触发：

| 触发词 | 典型用户表述 | 本 Skill 的响应 |
|--------|-------------|----------------|
| 多智能体 | "用多智能体方式帮我做..." | 启动任务拆解流程 |
| Agent协作 | "让几个 Agent 分工..." | 分配角色并编排依赖 |
| 任务编排 | "帮我编排一下这个任务的执行顺序" | 生成依赖关系图 |
| 分工协同 | "这个活分给几个角色一起干" | 拆解子任务并分配 |
| 多角色协作 | "让研究员和分析师配合..." | 创建多角色 Agent 组 |
| 智能体调度 | "调度多个 AI 分别处理不同部分" | 执行并行/串行调度 |

**大白话示例**：

- "帮我写一份咖啡市场分析报告，用多智能体分工" → 触发拆解为 3 个 Agent：数据收集、竞品分析、报告撰写
- "让一个 Agent 查资料，另一个做总结" → 触发两阶段依赖流程

---

## 三、标准流程

### 前置条件

| 条件 | 要求 |
|------|------|
| 任务描述 | 需包含明确目标（如"分析XX市场"），模糊描述将触发澄清提问 |
| 输出格式偏好 | 可选，默认输出 Markdown 结构化报告 |
| 角色自定义 | 可选，用户可指定 Agent 角色名称与职责 |

### 执行步骤

**Step 1：任务解析**
- 读取用户输入，提取核心目标、范围约束、输出要求
- 若信息不足（如缺少时间范围、地域限定），输出提示：[需核实:任务范围]

**Step 2：任务拆解**
- 将任务拆分为 2~5 个子任务，每个子任务对应一个 Agent
- 拆解原则：子任务间低耦合、高内聚；依赖关系明确

**Step 3：角色分配与依赖编排**
- 为每个子任务分配角色名（如"数据采集员""趋势分析师"）
- 确定执行顺序：串行（A→B→C）或并行（A∥B→C）

**Step 4：逐 Agent 执行**
- 按依赖顺序调用各 Agent，前序 Agent 的输出作为后续 Agent 的输入
- 每个 Agent 执行时遵循独立推理，不跨 Agent 共享中间推理过程

**Step 5：结果汇总与结构化**
- 收集所有 Agent 输出，按统一模板整合
- 对缺失或不确定字段标注 [需核实:字段名]

**Step 6：输出报告**

### 输出规范

```markdown
# [任务名称] 分析报告

## 1. 执行概览
- 拆解 Agent 数量：N
- 执行模式：串行/并行/混合
- 总耗时：约 X 分钟（估算）

## 2. 子任务结果
### Agent 1：[角色名]
- 输入：[前序输出摘要]
- 输出：[核心结论]

### Agent 2：[角色名]
...

## 3. 综合结论
[汇总各 Agent 结论，形成最终输出]

## 4. 置信度说明
- 高置信度字段：...
- 需核实字段：[需核实:具体字段]
```

---

## 四、置信度门控

本 Skill 遵循"不编造"原则，在以下情况输出占位符：

| 场景 | 输出格式 | 示例 |
|------|---------|------|
| 数据缺失 | [需核实:字段名] | [需核实:2025年Q1市场规模] |
| 信息矛盾 | [需核实:矛盾点描述] | [需核实:两份来源对增长率说法不一致] |
| 超出知识范围 | [需核实:该领域超出训练数据范围] | [需核实:2026年技术路线预测] |
| 用户输入模糊 | [需核实:具体需求] | [需核实:目标市场地域范围] |

**门控规则**：
- 置信度 < 60% 的字段必须标注
- 标注字段不参与后续 Agent 的推理输入（避免错误传播）
- 用户可补充信息后重新触发执行

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|---------|---------|
| E001 | 任务描述过短/模糊 | "任务目标不够明确，请补充具体需求" | 用户补充目标、范围、输出要求后重试 |
| E002 | 拆解失败（无法拆分为 2~5 个子任务） | "该任务过于简单或过于复杂，无法自动拆解" | 建议用户手动指定子任务列表 |
| E003 | 依赖循环检测 | "检测到子任务间存在循环依赖，请调整" | 用户重新描述任务或指定执行顺序 |
| E004 | Agent 执行超时 | "某 Agent 执行时间过长，已中断" | 简化该子任务描述后重试 |
| E005 | 输出格式不合法 | "汇总结果无法按模板格式化" | 检查各 Agent 输出是否为纯文本，重新执行 |
| E006 | 置信度过低 | "关键字段置信度低于阈值，已标注占位符" | 用户补充数据源或接受标注结果 |

---

## 六、FAQ 反模式对照

| # | 常见坑 | 反模式（错误做法） | 正确做法 |
|---|--------|-------------------|---------|
| 1 | 任务描述过于笼统 | "帮我分析一下市场" | 明确范围："分析中国 2024 年咖啡市场的规模、主要品牌份额、增长趋势" |
| 2 | 期望实时数据 | 认为输出包含最新数据 | 主动声明数据截止时间，或自行补充最新数据源 |
| 3 | 忽略置信度标注 | 直接引用 [需核实] 字段作为事实 | 对标注字段进行人工核实后再使用 |
| 4 | 强行拆分简单任务 | 把"计算 2+2"拆成 3 个 Agent | 简单任务直接执行，不触发多 Agent 流程 |
| 5 | 依赖关系混乱 | 让 Agent B 和 C 互相等待对方输出 | 明确指定单向依赖，或改为并行执行 |

---

## 七、渐进式披露：分层次阅读路径

### 🚀 速查卡（30 秒上手）

1. 输入任务描述（含目标、范围）
2. 系统自动拆解为 2~5 个 Agent
3. 按依赖顺序执行
4. 输出结构化报告（含置信度标注）

### 📖 新手路径（首次使用）

1. 阅读「能力边界」了解适用范围
2. 使用「触发方式」中的场景示例，尝试简单任务
3. 观察「标准流程」中的步骤，理解执行过程
4. 遇到问题时查阅「错误码体系」

### 🔧 进阶路径（熟练用户）

1. 自定义 Agent 角色与职责（在任务描述中指定："让数据收集员负责...，让分析师负责..."）
2. 设计复杂流程（并行分支、条件跳转）：描述中明确"先并行做 A 和 B，再根据 A 的结果决定是否做 C"
3. 调整置信度阈值，控制输出质量（默认 60%，可要求"低于 80% 的字段都标注"）
4. 结合外部工具，扩展能力边界（如将输出导入表格工具进一步处理）

---

## 八、用户协议

<!-- user-agreement-injected -->

**1. 责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的输出仅供参考，不构成任何专业建议或决策依据。

**2. 禁止反向工程**：不得对本 Skill 的提示词、处理逻辑、内部机制进行反向工程、破解、提取或用于训练竞争性模型。

**3. 合规使用**：使用者应确保使用场景符合当地法律法规，不得用于生成违法、侵权、有害内容。

**4. 无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 协同流工作室

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

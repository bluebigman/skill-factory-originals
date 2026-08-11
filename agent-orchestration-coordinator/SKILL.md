---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agent-orchestration-coordinator
name: agent-orchestration-coordinator
displayName: 多代理协作 任务编排 进度跟踪
description: 协调多个AI代理分工协作，跟踪任务进度并汇总结果，适用于复杂工作流编排。
version: 1.0.2
rules_version: cpr-20260811-n351
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agent-orchestration-coordinator
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Studio
agent_created: true
trigger_words: ["多智能体协作", "任务编排", "工作流协调", "agent调度", "代理分工", "子任务拆解", "进度汇总"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 多代理协作编排器（Agent Orchestration Coordinator）

## 一、能力边界速查卡

### 1.1 能做什么

| 能力项 | 说明 | 输出示例 |
|--------|------|----------|
| 任务结构化拆解 | 将自然语言任务拆为可独立执行的子任务清单 | `[{"id":"T1","desc":"检索行业报告","deps":[]}]` |
| 代理角色匹配 | 根据子任务类型推荐代理角色或工具类型 | `{"T1":"检索代理","reason":"需要外部数据获取"}` |
| 进度状态跟踪 | 维护子任务状态机，支持中途查询 | `{"T1":"执行中","T2":"已完成"}` |
| 结果汇总与冲突消解 | 合并各代理结果，矛盾结论并列展示 | `{"conflict":true,"views":[...]}` |
| 置信度标注 | 对汇总结果标注高/中/低置信度 | `{"confidence":"low","flag":"[需核实:数据来源]"}` |

### 1.2 不能做什么

- **不能执行子任务本身**：本技能只负责编排与协调，不替代各代理执行具体工作。
- **不能保证代理输出正确性**：代理返回的结果可能包含错误，需通过置信度门控提示人工复核。
- **不能处理无限循环依赖**：若子任务间存在循环依赖，将报错并终止编排。
- **不能跨会话持久化状态**：进度状态仅存在于当前会话，重启后需重新初始化。

### 1.3 适用对象

- 需要将复杂任务拆解为多个子任务并行处理的场景
- 需要协调多个AI代理（如检索、分析、写作、审查）协作的流程
- 需要跟踪任务进度并汇总结果的团队或个人

---

## 二、触发方式

### 2.1 触发词

- 主触发词：`多智能体协作`、`任务编排`、`工作流协调`、`agent调度`
- 补充触发词：`代理分工`、`子任务拆解`、`进度汇总`

### 2.2 场景映射表

| 用户说（大白话） | 触发动作 | 示例输入 |
|------------------|----------|----------|
| "帮我安排几个AI一起干活" | 任务拆解 + 角色匹配 | "调研竞品并写一份报告" |
| "这个项目分几步走？" | 任务结构化拆解 | "做一个市场分析" |
| "现在进度到哪了？" | 进度状态查询 | 无（直接查询） |
| "把结果汇总一下" | 结果合并 + 冲突消解 | 无（基于已有结果） |
| "这几个结论矛盾怎么办" | 冲突并列展示 | 无（自动检测） |

---

## 三、标准流程

### 3.1 前置条件

- 输入参数：任务描述（字符串）或结构化任务列表（JSON数组）
- 可选参数：代理角色配置（如 `{"检索":"web-search-agent"}`）
- 环境要求：无特殊依赖，纯逻辑处理

### 3.2 执行步骤

**步骤1：任务解析与拆解**

- 读取输入的任务描述，识别核心目标与约束条件
- 拆解为子任务清单，每个子任务包含：`id`、`desc`、`deps`（依赖列表）、`type`（任务类型）
- 任务类型枚举：`retrieval`（检索）、`analysis`（分析）、`writing`（写作）、`review`（审查）

**步骤2：代理角色匹配**

- 根据子任务类型推荐代理角色：

| 任务类型 | 推荐代理 | 匹配理由 |
|----------|----------|----------|
| retrieval | 检索代理 | 需要外部数据获取能力 |
| analysis | 分析代理 | 需要数据处理与推理能力 |
| writing | 写作代理 | 需要文本生成能力 |
| review | 审查代理 | 需要质量校验能力 |

**步骤3：进度状态初始化**

- 为每个子任务初始化状态：`pending`（待分配）
- 根据依赖关系确定执行顺序：无依赖任务标记为 `ready`（可执行）

**步骤4：执行调度与状态更新**

- 按依赖顺序分配任务给对应代理
- 代理开始执行后，状态更新为 `running`（执行中）
- 代理返回结果后，状态更新为 `completed`（已完成）
- 若代理返回错误，状态更新为 `failed`（失败），并记录错误信息

**步骤5：结果汇总与冲突消解**

- 收集所有已完成子任务的结果
- 按预设模板合并结果（模板见3.3节）
- 检测同一问题上的矛盾结论：若存在，并列展示并标注差异

**步骤6：置信度标注与输出**

- 对每个汇总结果标注置信度（高/中/低）
- 置信度为"低"的条目自动标记 `[需核实:字段名]`
- 输出结构化结果，并给出下一步建议

### 3.3 输出规范

输出格式为JSON，包含以下字段：

```json
{
  "task_id": "string",
  "status": "completed",
  "subtasks": [
    {
      "id": "T1",
      "desc": "string",
      "status": "completed",
      "result": "any",
      "confidence": "high|medium|low",
      "flags": ["[需核实:字段名]"]
    }
  ],
  "summary": {
    "total": 5,
    "completed": 5,
    "failed": 0,
    "conflicts": []
  },
  "next_steps": ["string"]
}
```

---

## 四、置信度门控

### 4.1 置信度判定规则

| 置信度 | 判定条件 | 处理方式 |
|--------|----------|----------|
| 高 | 多个独立代理结果一致，且数据来源可靠 | 正常输出 |
| 中 | 单个代理结果，或数据来源单一 | 正常输出，但提示可复核 |
| 低 | 代理结果存在矛盾，或数据缺失 | 标记 `[需核实:字段名]`，提示用户介入 |

### 4.2 信息不足时的处理

- 当某个字段信息不足时，输出 `[需核实:字段名]` 占位符，**不编造数据**
- 示例：若代理未返回"市场规模"数据，输出 `[需核实:市场规模]`，而非猜测数值

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 输入任务描述为空 | "请提供需要编排的任务描述" | 输入非空任务描述 |
| E002 | 子任务依赖循环 | "检测到循环依赖，请检查任务依赖关系" | 调整依赖关系，消除循环 |
| E003 | 代理角色不匹配 | "子任务类型无法匹配到合适的代理角色" | 检查任务类型枚举，或自定义代理配置 |
| E004 | 代理执行超时 | "代理执行超时，请检查代理状态或重试" | 等待后重试，或检查代理服务 |
| E005 | 结果汇总失败 | "结果汇总时发生错误，请检查各子任务结果格式" | 检查子任务结果是否符合预期格式 |
| E006 | 置信度评估失败 | "无法评估结果置信度，请检查数据完整性" | 补充缺失数据后重新评估 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式示例 | 正确做法 |
|----|------------|----------|
| 任务拆解过粗 | 将"写报告"作为一个子任务，未拆解为检索、分析、写作 | 拆解为多个可独立执行的子任务 |
| 忽略依赖关系 | 所有子任务标记为无依赖，导致并行执行时数据缺失 | 明确标注依赖关系，确保执行顺序正确 |
| 不处理冲突 | 多个代理结果矛盾时直接取第一个 | 并列展示矛盾结论，标注差异 |
| 置信度虚高 | 所有结果都标注为"高"置信度 | 根据数据来源和一致性客观评估 |
| 忽略失败任务 | 子任务失败后继续汇总，导致结果不完整 | 标记失败状态，提示用户处理 |

### 6.2 反模式对照表

| 反模式 | 问题 | 改进方案 |
|--------|------|----------|
| 一次性分配所有任务 | 资源浪费，依赖任务无法执行 | 按依赖关系分批分配 |
| 不提供进度查询接口 | 用户无法了解执行状态 | 提供 `get_progress` 接口 |
| 汇总时丢弃原始数据 | 无法追溯结果来源 | 保留原始结果，标注来源 |
| 自动解决所有冲突 | 可能掩盖真实差异 | 并列展示，由用户决策 |

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

1. 输入任务描述 → 自动拆解为子任务
2. 每个子任务匹配代理角色 → 按依赖顺序执行
3. 查询进度 → 获取状态
4. 汇总结果 → 查看置信度标注

### 7.2 进阶路径（有经验用户）

- **自定义代理配置**：通过 `agent_config` 参数指定特定代理
- **自定义汇总模板**：通过 `template` 参数指定结果合并格式
- **冲突处理策略**：通过 `conflict_policy` 参数选择"并列展示"或"投票表决"
- **置信度阈值调整**：通过 `confidence_threshold` 参数调整低置信度判定标准

### 7.3 完整参数表

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `task_description` | string | 是 | 无 | 自然语言任务描述 |
| `agent_config` | object | 否 | 默认映射 | 自定义代理角色映射 |
| `template` | object | 否 | 默认模板 | 结果汇总模板 |
| `conflict_policy` | string | 否 | `"show_all"` | 冲突处理策略 |
| `confidence_threshold` | number | 否 | 0.7 | 低置信度判定阈值 |

---

## 八、使用示例

### 8.1 简单示例

**输入**：
```
任务：调研新能源汽车市场并撰写分析报告
```

**输出**：
```json
{
  "task_id": "task_001",
  "status": "completed",
  "subtasks": [
    {
      "id": "T1",
      "desc": "检索新能源汽车市场数据",
      "status": "completed",
      "result": "2025年市场规模约5000亿元",
      "confidence": "high"
    },
    {
      "id": "T2",
      "desc": "分析竞争格局",
      "status": "completed",
      "result": "前五名企业占据60%市场份额",
      "confidence": "medium"
    },
    {
      "id": "T3",
      "desc": "撰写分析报告",
      "status": "completed",
      "result": "报告全文...",
      "confidence": "high"
    }
  ],
  "summary": {
    "total": 3,
    "completed": 3,
    "failed": 0,
    "conflicts": []
  },
  "next_steps": ["可进一步分析政策影响"]
}
```

### 8.2 冲突场景示例

**输入**：
```
任务：评估某技术方案的可行性
```

**输出**（节选）：
```json
{
  "subtasks": [
    {
      "id": "T2",
      "desc": "技术可行性分析",
      "status": "completed",
      "result": {
        "conflict": true,
        "views": [
          {"agent": "分析代理A", "conclusion": "可行", "reason": "技术成熟度达80%"},
          {"agent": "分析代理B", "conclusion": "不可行", "reason": "成本超预算30%"}
        ],
        "difference": "两代理对成本评估标准不一致"
      },
      "confidence": "low",
      "flags": ["[需核实:成本评估标准]"]
    }
  ]
}
```

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因使用本 Skill 产生的任何直接或间接损失，作者不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码。
3. **合规使用**：使用者应确保使用本 Skill 的行为符合当地法律法规及平台规定。
4. **内容责任**：使用者应对使用本 Skill 生成的内容负全部责任，包括但不限于内容的合法性、准确性和适当性。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 FlowForge Studio

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

---

**版本历史**

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0.0 | 2026-08-11 | 初始版本发布 |

---

**免责声明**：本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档，并根据实际场景调整配置。作者不对因使用本 Skill 而产生的任何结果承担责任。

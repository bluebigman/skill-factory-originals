---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: awesome-gamedev-agent-skills
name: awesome-gamedev-agent-skills
displayName: 游戏开发 智能路由 技能编排
description: 游戏开发Agent技能路由器：按工程任务自动装载对应技能模块。
version: 1.0.1
rules_version: cpr-20260809-n251
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/awesome-gamedev-agent-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["gamedev", "游戏开发", "技能路由", "skill router", "游戏工程", "agent skills"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# awesome-gamedev-agent-skills 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 核心定位

本技能是一个**游戏开发领域的 Agent 技能路由器**。它不直接编写游戏代码，而是根据你当前所处的工程任务（如"处理玩家输入""生成关卡数据""调试战斗数值"），自动识别并装载最合适的下游技能模块，让 AI 编码代理在正确的上下文中执行操作。

### 1.2 能做清单

| 编号 | 能力项 | 说明 |
|------|--------|------|
| C1 | 任务意图识别 | 从用户描述中提取工程阶段、技术栈、目标产物 |
| C2 | 技能路由匹配 | 将任务映射到预定义的技能模块（如 `level-designer`、`balance-tuner`） |
| C3 | 上下文打包 | 将用户输入、仓库文件列表、相关代码片段组装为下游技能的标准输入 |
| C4 | 置信度标注 | 对路由结果给出匹配置信度，低置信时主动询问 |
| C5 | 批量任务分发 | 支持一次提交多个子任务，按依赖关系排序后逐个路由 |

### 1.3 不能做清单

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不直接生成游戏代码 | 路由完成后，实际编码由下游技能执行 |
| L2 | 不解析二进制资源 | 不接受 `.uasset`、`.prefab` 等二进制格式作为输入 |
| L3 | 不执行运行时调试 | 不连接游戏进程，不做内存读写或断点调试 |
| L4 | 不保证路由绝对正确 | 语义模糊时输出 `[需核实:意图]` 占位，等待用户确认 |
| L5 | 不处理非游戏领域任务 | 如"写一封邮件""做财务表格"等，直接返回错误码 `E_DOMAIN` |

### 1.4 适用对象

- **AI 编码代理**：作为中间层，为下游游戏开发技能提供统一入口。
- **游戏开发工程师**：通过自然语言描述任务，获得结构化的技能调用建议。
- **技术负责人**：批量提交任务清单，获取按依赖排序的执行计划。

---

## 二、触发方式

### 2.1 触发词

当输入中出现以下关键词或语义时，本技能被激活：

- `gamedev`、`游戏开发`、`游戏工程`
- `技能路由`、`skill router`、`装载技能`
- `关卡设计`、`数值平衡`、`战斗系统`、`UI 界面`、`音效集成`
- `帮我处理这个游戏任务`、`下一步该用什么技能`

### 2.2 场景映射表

| 用户说（大白话） | 路由目标 | 触发置信度 |
|------------------|----------|------------|
| "帮我看看这个关卡的地形数据怎么生成" | `level-designer` | 0.92 |
| "玩家攻击力调多少才不破坏平衡" | `balance-tuner` | 0.87 |
| "这个 UI 按钮点击没反应" | `ui-debugger` | 0.78 |
| "把敌人 AI 的寻路逻辑优化一下" | `ai-pathfinder` | 0.85 |
| "帮我整理一下项目里所有音效文件" | `asset-organizer` | 0.81 |
| "写个邮件给外包团队" | 拒绝（`E_DOMAIN`） | — |

---

## 三、标准流程

### 3.1 前置条件

| 条件编号 | 条件内容 | 缺失时行为 |
|----------|----------|------------|
| P1 | 用户输入至少包含一个明确的任务动词（如"生成""调试""优化"） | 返回 `E_NO_VERB`，提示补充动词 |
| P2 | 输入中可识别出至少一个游戏领域实体（如"关卡""角色""数值"） | 返回 `E_NO_ENTITY`，提示补充领域词 |
| P3 | 若涉及文件操作，需提供文件路径或 URL | 返回 `E_NO_PATH`，提示补充路径 |
| P4 | 若输入为批量任务，需提供任务分隔符（如换行、逗号） | 返回 `E_NO_SEPARATOR`，提示补充分隔符 |

### 3.2 执行步骤

**Step 1：输入规范化**

将用户输入统一为如下结构：

```
{
  "raw_text": "原始输入字符串",
  "task_verb": "提取的动词",
  "domain_entity": "提取的领域实体",
  "file_paths": ["路径列表，可为空"],
  "batch_mode": true/false,
  "custom_format": "用户指定的输出格式，可为空"
}
```

**Step 2：意图解析**

- 使用关键词词典匹配 `task_verb` 和 `domain_entity`。
- 词典覆盖 5 大类、30 个子类技能（见附录 A）。
- 若匹配度低于 0.6，进入**置信度门控**流程（见第四节）。

**Step 3：技能路由**

根据解析结果，从技能注册表中选取最匹配的技能模块。路由规则：

| 优先级 | 匹配条件 | 路由动作 |
|--------|----------|----------|
| 1 | 动词 + 实体 完全匹配 | 直接路由，置信度 = 0.95 |
| 2 | 动词匹配、实体近义匹配 | 路由 + 置信度 = 0.80 |
| 3 | 仅动词匹配 | 路由 + 置信度 = 0.65，附加候选列表 |
| 4 | 均不匹配 | 返回 `E_NO_MATCH`，列出最接近的 3 个技能 |

**Step 4：上下文打包**

将用户输入、匹配到的技能说明、相关文件片段（若提供路径）组装为下游技能的标准输入 JSON。

**Step 5：输出生成**

按 3.3 节输出规范生成结果，并执行自查。

### 3.3 输出规范

输出为 Markdown 格式，包含以下字段：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `routed_skill` | string | 是 | 路由到的技能模块名 |
| `confidence` | float | 是 | 置信度，范围 0.0~1.0 |
| `input_payload` | object | 是 | 传递给下游技能的标准输入 |
| `alternative_skills` | array | 否 | 备选技能列表（置信度 < 0.8 时必填） |
| `warnings` | array | 否 | 处理过程中的警告信息 |
| `needs_confirmation` | boolean | 是 | 是否需要用户二次确认 |

**示例输出：**

```markdown
## 路由结果

- **路由技能**：`balance-tuner`
- **置信度**：0.87
- **需确认**：否

### 输入载荷

```json
{
  "task": "调整玩家攻击力",
  "current_value": 15,
  "target_metric": "平均战斗时长",
  "constraints": ["不超过 20", "不低于 10"]
}
```

### 备选技能

1. `combat-simulator`（置信度 0.62）
2. `stat-visualizer`（置信度 0.55）

### 警告

- 未提供具体数值范围，已使用默认约束。
```

---

## 四、置信度门控

### 4.1 门控规则

当满足以下任一条件时，输出中必须包含 `[需核实:字段]` 占位符，**禁止编造**：

| 条件 | 占位符示例 | 说明 |
|------|------------|------|
| 用户未指定输出格式 | `[需核实:输出格式]` | 默认使用 Markdown，但需确认 |
| 文件路径不存在 | `[需核实:文件路径]` | 不猜测路径，直接询问 |
| 任务动词有歧义 | `[需核实:任务意图]` | 如"处理"可指优化、重构、修复 |
| 数值参数缺失 | `[需核实:参数值]` | 如调整攻击力但未给数值 |

### 4.2 门控流程

```
解析输入 → 检测缺失字段 → 缺失？
  ├─ 是 → 生成 [需核实:字段] 占位 → 输出部分结果 + 询问列表
  └─ 否 → 正常输出完整结果
```

### 4.3 示例

**用户输入**："帮我优化一下这个关卡的性能"

**输出**：

```markdown
## 路由结果

- **路由技能**：`level-optimizer`
- **置信度**：0.72
- **需确认**：是

### 缺失信息

- [需核实:性能指标]：您希望优化哪项指标？(帧率 / 加载时间 / 内存占用)
- [需核实:目标平台]：PC / 移动端 / 主机？
- [需核实:文件路径]：请提供关卡文件的路径或 URL。

### 部分输入载荷

```json
{
  "task": "性能优化",
  "target_metric": "[需核实:性能指标]",
  "platform": "[需核实:目标平台]",
  "file_path": "[需核实:文件路径]"
}
```
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E_DOMAIN` | 非游戏领域任务 | "该任务不属于游戏开发领域，本技能仅处理游戏工程相关请求。" | 请重新描述为游戏开发任务，或使用其他技能 |
| `E_NO_VERB` | 缺少任务动词 | "未检测到明确的任务动词（如生成、调试、优化）。" | 在输入中加入动词，例如"生成关卡地形" |
| `E_NO_ENTITY` | 缺少领域实体 | "未检测到游戏领域实体（如关卡、角色、数值）。" | 在输入中指明对象，例如"调整玩家攻击力" |
| `E_NO_PATH` | 缺少文件路径 | "涉及文件操作但未提供路径或 URL。" | 补充文件路径，或说明无需文件操作 |
| `E_NO_SEPARATOR` | 批量任务缺少分隔符 | "批量任务需使用换行或逗号分隔各子任务。" | 重新输入，用换行分隔每个任务 |
| `E_NO_MATCH` | 无匹配技能 | "未找到匹配的技能模块。以下为最接近的 3 个：..." | 从候选列表中选择，或重新描述任务 |
| `E_PARSE_FAIL` | 输入解析失败 | "输入内容无法解析，请检查格式。" | 参考正确的输入格式示例（见 5.1） |
| `E_BATCH_EMPTY` | 批量任务为空 | "批量任务列表为空，未提取到任何子任务。" | 确认输入内容非空，且分隔符正确 |

### 5.1 正确输入格式示例

```
# 单任务格式
生成一个 10x10 的迷宫关卡，出口在右下角

# 批量任务格式（换行分隔）
优化敌人 AI 寻路
调整玩家初始金币为 500
生成 3 种不同风格的 UI 按钮
```

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 坑编号 | 常见错误做法 | 反模式（正确做法） |
|--------|--------------|---------------------|
| F1 | 用户说"帮我处理一下"，直接路由到 `general-processor` | 应触发置信度门控，询问具体任务类型，避免模糊路由 |
| F2 | 文件路径不存在时，猜测一个相似路径继续执行 | 应输出 `[需核实:文件路径]`，等待用户提供正确路径 |
| F3 | 批量任务中某个子任务失败，整个流程终止 | 应跳过失败项，记录错误，继续处理其余子任务，最后汇总 |
| F4 | 置信度低于 0.6 时仍强行路由 | 应返回 `E_NO_MATCH`，列出候选技能，由用户选择 |
| F5 | 输出格式与用户预期不符时，自行决定格式 | 应在首次输出时询问格式偏好，或使用 `[需核实:输出格式]` 占位 |

### 6.2 反模式示例

**错误做法**：

```
用户：帮我弄一下这个
AI：已路由到 general-processor，正在执行...
```

**正确做法**：

```
用户：帮我弄一下这个
AI：检测到任务意图不明确，请补充以下信息：
  [需核实:任务意图] 您希望执行什么操作？（生成/优化/调试/重构）
  [需核实:目标对象] 针对哪个游戏元素？（关卡/角色/数值/UI）
```

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 输入任务描述（含动词 + 游戏元素）
2. 收到路由结果（技能名 + 置信度）
3. 置信度 ≥ 0.8 → 直接执行
4. 置信度 < 0.8 → 查看备选技能，确认后执行
5. 有 [需核实:字段] → 补充信息后重试
```

### 7.2 新手阅读路径

- 先读**第一节**了解能力边界，避免期望过高。
- 再读**第三节**的标准流程，掌握基本用法。
- 遇到报错时查阅**第五节**错误码表。
- 最后读**第六节**反模式，避免常见错误。

### 7.3 进阶阅读路径

- 深入**第四节**置信度门控，理解路由决策逻辑。
- 研究**附录 A**技能注册表，了解全部可路由技能。
- 结合**批量任务**功能，设计自动化工作流。
- 自定义技能注册表，扩展路由范围。

---

## 附录 A：技能注册表（节选）

| 技能模块 | 触发动词 | 领域实体 | 默认置信度 |
|----------|----------|----------|------------|
| `level-designer` | 生成、设计、创建 | 关卡、地图、地形 | 0.90 |
| `balance-tuner` | 调整、平衡、修改 | 数值、属性、参数 | 0.87 |
| `ui-debugger` | 修复、调试、排查 | UI、按钮、界面 | 0.78 |
| `ai-pathfinder` | 优化、改进、重写 | AI、寻路、导航 | 0.85 |
| `asset-organizer` | 整理、分类、归档 | 资源、音效、贴图 | 0.81 |
| `combat-simulator` | 模拟、测试、验证 | 战斗、技能、伤害 | 0.83 |
| `stat-visualizer` | 可视化、展示、绘制 | 数据、统计、图表 | 0.76 |
| `level-optimizer` | 优化、提升、加速 | 性能、帧率、加载 | 0.72 |

---

## 用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的路由建议和输出结果仅供参考，不构成任何形式的保证或承诺。因使用本 Skill 导致的任何直接或间接损失，Skill 作者及贡献者不承担任何责任。

2. **禁止反向工程**：使用者不得对本 Skill 的底层逻辑、路由算法、技能注册表结构进行反向工程、反编译、破解或试图提取源代码。不得移除、篡改或绕过本 Skill 中的任何版权声明、许可证信息或合规标记。

3. **合规使用**：使用者应确保使用本 Skill 的行为符合当地法律法规及所在组织的政策要求。不得将本 Skill 用于任何非法目的或侵犯第三方权益的行为。

4. **免责声明**：本 Skill 由 AI 辅助生成，可能存在未知缺陷或局限性。使用者应在实际项目中充分测试后再投入使用。

---

## 许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 SkillForge Studio

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

*文档版本：1.0.0 | 最后更新：2026-08-09 | 生成方式：AI 辅助*

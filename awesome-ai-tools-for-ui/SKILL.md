---
slug: awesome-ai-tools-for-ui
name: awesome-ai-tools-for-ui
displayName: UI设计 AI工具导航
description: 精选AI辅助界面设计工具，助你快速构建优质UI/UX方案。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["awesome-ai-tools-for-ui", "AI UI工具", "界面设计工具", "UI设计资源", "AI辅助设计", "UI工具清单", "设计工具推荐"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# awesome-ai-tools-for-ui — UI设计 AI工具导航

本 Skill 用于收集、解析、分类并输出 AI 辅助界面设计工具清单。你提供工具信息（名称、描述、分类等），我负责整理成结构化表格或分组列表，并对不确定的字段明确标注，绝不臆造。

---

## 一、能力边界（一页纸速查卡）

| 维度 | 说明 |
|------|------|
| ✅ 能做 | 接收用户提供的工具信息（文本、列表、表格均可） |
| ✅ 能做 | 提取工具名称、用途描述、适用场景、分类标签、价格模式、平台支持等字段 |
| ✅ 能做 | 按分类（默认）或用户指定维度（如价格、平台）分组排序 |
| ✅ 能做 | 输出 Markdown 表格或分组列表，字段缺失时标注 `[需核实:字段名]` |
| ❌ 不能做 | 自行搜索或补充用户未提供的工具信息 |
| ❌ 不能做 | 验证工具的真实性、时效性或可用性 |
| ❌ 不能做 | 提供任何形式的购买建议或效果承诺 |
| ❌ 不能做 | 对工具进行排名或评分（除非用户明确提供评分数据） |

**适用对象**：UI/UX 设计师、产品经理、前端开发者、设计工具研究者，以及任何需要快速整理 AI 设计工具清单的人。

---

## 二、触发方式

当你的输入包含以下任一场景时，本 Skill 自动激活：

| 触发词/短语 | 场景示例（大白话） |
|-------------|-------------------|
| "AI UI工具" | "帮我整理一下现在好用的 AI UI 工具" |
| "界面设计工具" | "有哪些界面设计工具推荐？我整理了一些信息你帮我归类" |
| "UI设计资源" | "这是我收集的 UI 设计资源，帮我按分类整理成表格" |
| "AI辅助设计" | "AI 辅助设计工具有哪些？我列了几个你帮我看看" |
| "awesome-ai-tools-for-ui" | 直接调用技能名 |
| "工具清单" | "帮我做一个设计工具清单，按价格分组" |
| "设计工具推荐" | "推荐一些设计工具，我提供信息你帮我整理" |

---

## 三、标准流程

### 前置条件

- 用户至少提供 1 条工具信息（名称 + 任意辅助字段）
- 若用户未提供任何信息，输出提示并等待输入

### 执行步骤

1. **收集输入** — 接收用户提供的工具信息，支持以下来源：
   - 纯文本列表（每行一个工具）
   - Markdown 表格
   - 逗号/分号分隔的字段串
   - 自然语言描述（如"XX工具，用于生成图标，免费，支持Web"）

2. **字段解析** — 从每条记录中提取以下字段：

   | 字段名 | 说明 | 是否必填 |
   |--------|------|----------|
   | `name` | 工具名称 | 是 |
   | `description` | 一句话功能描述 | 否 |
   | `category` | 分类（如：原型设计、图标生成、配色方案、代码转UI等） | 否 |
   | `pricing` | 价格模式（免费/付费/免费增值） | 否 |
   | `platform` | 支持平台（Web/Windows/macOS/iOS/Android/插件） | 否 |
   | `url` | 官网或产品链接 | 否 |

3. **分类整理** — 按用户指定维度排序，默认按 `category` 分组。若某工具缺少 `category` 字段，归入"未分类"组。

4. **置信度标注** — 对无法确认的字段，输出 `[需核实:字段名]` 占位符，不猜测、不编造。

5. **输出生成** — 按约定格式输出 Markdown 表格或分组列表。

### 输出规范

**表格格式**（当工具数量 ≤ 15 且字段完整时）：

```markdown
| 工具名称 | 功能描述 | 分类 | 价格 | 平台 | 链接 |
|----------|----------|------|------|------|------|
| Figma AI | 智能布局建议 | 原型设计 | 免费增值 | Web | [链接](url) |
```

**分组列表格式**（当工具数量 > 15 或用户指定分组时）：

```markdown
### 原型设计
- **Figma AI** — 智能布局建议（免费增值 / Web）[链接](url)

### 图标生成
- **IconGen** — 文字描述生成图标（付费 / Web）[需核实:url]
```

---

## 四、置信度门控

| 情况 | 处理方式 |
|------|----------|
| 用户未提供 `url` | 输出 `[需核实:url]`，不主动搜索 |
| 用户未提供 `pricing` | 输出 `[需核实:pricing]` |
| 用户提供的分类含糊（如"好用"） | 归入"未分类"，并提示用户补充 |
| 用户提供的信息自相矛盾 | 以用户最新表述为准，标注 `[需核实:冲突字段]` |
| 输入为空 | 输出引导提示，不生成空表格 |

**示例**：

用户输入："IconGen 这个工具不错，能根据描述生成图标。"

输出：

```markdown
| 工具名称 | 功能描述 | 分类 | 价格 | 平台 | 链接 |
|----------|----------|------|------|------|------|
| IconGen | 根据描述生成图标 | 未分类 | [需核实:pricing] | [需核实:platform] | [需核实:url] |
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入为空 | "未检测到工具信息，请提供至少一个工具的名称和描述。" | 请补充工具信息后重试 |
| `E002` | 字段解析失败 | "无法从输入中识别有效字段，请检查格式。" | 使用"工具名 - 描述 - 分类"的格式重新输入 |
| `E003` | 分类冲突 | "检测到多个分类维度，请指定排序方式。" | 明确指定按 `category`、`pricing` 或 `platform` 分组 |
| `E004` | 信息自相矛盾 | "输入中存在冲突信息，已按最新表述处理。" | 确认最终版本后重新提交 |
| `E005` | 输出格式异常 | "输出生成失败，请重试或减少工具数量。" | 分批次提交工具信息 |

---

## 六、FAQ 反模式

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 编造信息 | 用户未提供 `url`，自行搜索并填入 | 输出 `[需核实:url]` 占位符 |
| 过度承诺 | "这个工具绝对好用" | 仅陈述用户提供的事实，不做评价 |
| 忽略冲突 | 用户前后说法矛盾，直接采用后一个 | 标注 `[需核实:冲突字段]` 并提示用户确认 |
| 格式混乱 | 混合使用表格和列表，无统一结构 | 按输出规范统一格式 |
| 分类过细 | 用户只给了 3 个工具，强行分 5 类 | 工具少时用表格，工具多时用分组 |

---

## 七、渐进式披露

### 速查卡（30 秒上手）

1. 输入工具信息（名称 + 描述即可）
2. 等待输出表格或分组列表
3. 检查 `[需核实:字段]` 占位符，补充信息后重新提交

### 新手路径（首次使用）

1. 阅读"能力边界"了解能做什么、不能做什么
2. 参考"触发方式"中的示例，用自然语言描述你的需求
3. 提交信息后，对照"输出规范"检查结果格式

### 进阶路径（熟练使用）

1. 批量提交工具信息（建议每次 10-20 条）
2. 指定分组维度（如按 `pricing` 分组，便于对比免费/付费工具）
3. 利用"错误码体系"快速定位输入格式问题
4. 结合"置信度门控"主动补充缺失字段，提升输出完整性

---

## 用户协议

**使用前请仔细阅读以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的信息整理与推荐服务仅供参考，不构成任何形式的专业建议或保证。

2. **禁止反向工程**：禁止对本 Skill 的提示词、处理逻辑、输出模板进行反向工程、破解、提取或二次分发。

3. **信息准确性**：本 Skill 输出的工具信息基于用户输入，不保证信息的完整性、准确性和时效性。使用者应自行核实关键信息。

4. **合规使用**：使用者应确保输入内容不违反任何法律法规，不侵犯第三方权益。

<!-- user-agreement-injected -->

---

## 许可证（License）

本 Skill 采用 MIT 许可证发布。

### MIT License

```
MIT License

Copyright (c) 2024 Lin Chen

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*

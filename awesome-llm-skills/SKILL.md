---
slug: awesome-llm-skills
name: awesome-llm-skills
displayName: 技能匹配 场景导航 能力速查
description: 快速匹配LLM技能场景，提供结构化处理与置信度标注的通用工作流。
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
trigger_words: ["awesome-llm-skills", "技能导航", "能力匹配", "场景速查", "技能清单", "技能检索", "场景定位", "能力盘点"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# awesome-llm-skills 技能导航与场景匹配工作流

## 一、能力边界速查卡

本 Skill 面向需要快速定位 LLM 技能适用场景、并希望以结构化方式提取信息的用户。它提供了一套通用的处理管线，帮助你在不确定使用哪个技能时，通过关键词触发、场景映射和置信度标注来获得可用的输出。

### 能做

| 能力项 | 说明 | 适用场景示例 |
|--------|------|--------------|
| 技能场景匹配 | 根据输入文本中的关键词，推荐最接近的技能方向 | 用户输入"帮我提取合同中的日期"，可匹配到信息提取类技能 |
| 结构化字段输出 | 按自定义 `fields` 参数输出 JSON 格式结果 | 从一段人物介绍中提取姓名、年龄、职业 |
| 置信度标注 | 对每个输出字段标注可信程度，低置信度字段以占位符标记 | 源文本缺少某字段时，输出 `[需核实:字段名]` |
| 批量处理 | 支持多段文本的批量处理，并在 `meta` 中返回统计信息 | 一次处理 100 条用户反馈，统计提取成功率 |
| 错误诊断 | 通过错误码体系定位失败原因，并给出修正建议 | 输出 `E1002` 时，按提示调整输入格式 |

### 不能做

| 限制项 | 说明 |
|--------|------|
| 不执行具体业务逻辑 | 本 Skill 不包含特定行业的判断规则（如法律条款有效性、医学诊断），仅做通用文本处理 |
| 不保证字段完整性 | 当源文本确实缺少信息时，不会编造内容，而是输出占位符 |
| 不进行语义推理 | 仅基于显式文本信息做提取，不做隐含含义的推断 |
| 不处理非 UTF-8 编码 | 输入必须为 UTF-8 编码的纯文本或 Markdown 格式 |

### 适用对象

- 需要快速评估某个 LLM 技能是否适合自己的场景的开发者
- 需要从非结构化文本中提取结构化字段的数据处理人员
- 希望建立标准化文本提取流程的团队

---

## 二、触发方式与场景映射

当你的输入包含以下关键词或意图时，本 Skill 会被触发：

| 触发词 | 场景描述 | 示例输入 |
|--------|----------|----------|
| 技能导航 / 技能清单 | 想了解有哪些技能可用，或需要技能全景图 | "给我列一下当前可用的技能清单" |
| 能力匹配 / 技能检索 | 有明确任务，但不确定用哪个技能 | "我想从简历里提取技能关键词，该用哪个？" |
| 场景速查 / 场景定位 | 想确认某个场景是否被覆盖 | "有没有处理 PDF 转文本的技能？" |
| 技能盘点 | 需要评估已有技能的覆盖范围和缺口 | "帮我盘点一下现有技能，看看哪些场景没覆盖" |

### 场景映射表

| 你的需求 | 推荐路径 | 预期输出 |
|----------|----------|----------|
| 想知道有哪些技能 | 直接输入"技能清单" | 返回技能列表及简要说明 |
| 有文本要提取字段 | 提供文本 + 指定 `fields` | 返回结构化 JSON |
| 不确定提取哪些字段 | 仅提供文本 | 返回默认字段的提取结果 + 建议字段列表 |
| 批量处理多段文本 | 传入数组格式 | 返回逐条结果 + 统计信息 |
| 遇到提取失败 | 查看错误码 | 返回错误码 + 修正建议 |

---

## 三、标准工作流

### 前置条件

- 输入文本为 UTF-8 编码的纯文本或 Markdown 格式
- 如需自定义输出字段，请预先定义 `fields` 参数（JSON 数组格式）
- 批量处理时，输入应为文本数组，单条文本不超过 10,000 字符

### 执行步骤

**Step 1：确认需求场景**

阅读「一、能力边界速查卡」，确认你的需求是否在本 Skill 的覆盖范围内。如果不在，请考虑其他专用技能。

**Step 2：构造输入**

根据你的需求，选择以下输入模式之一：

| 模式 | 输入格式 | 示例 |
|------|----------|------|
| 技能查询 | 纯文本，包含触发词 | `技能清单` |
| 单条提取 | 文本 + `fields` 参数 | `{"text": "张三，35岁，工程师", "fields": ["name", "age", "job"]}` |
| 批量提取 | 文本数组 + `fields` 参数 | `{"texts": [...], "fields": ["name"]}` |

**Step 3：执行并获取输出**

系统将按以下流程处理：

1. 解析输入，识别触发模式
2. 匹配场景映射表，确定处理管线
3. 执行字段提取，逐字段标注置信度
4. 组装输出 JSON，包含 `data` 和 `meta` 两部分

**输出规范：**

```json
{
  "data": {
    "name": "张三",
    "age": "35",
    "job": "工程师"
  },
  "meta": {
    "confidence": { "name": 0.98, "age": 0.95, "job": 0.92 },
    "missing_fields": [],
    "processing_time_ms": 120
  }
}
```

当某字段无法从源文本中提取时，`data` 中该字段值为 `[需核实:字段名]`，`meta.confidence` 中对应值为 `0`，并计入 `missing_fields`。

---

## 四、置信度门控机制

本 Skill 采用置信度门控策略，确保输出结果的可追溯性和诚实性。

### 置信度等级

| 等级 | 置信度区间 | 含义 | 处理方式 |
|------|------------|------|----------|
| 高 | 0.85 - 1.0 | 字段值直接从源文本中明确提取 | 直接输出 |
| 中 | 0.60 - 0.84 | 字段值通过上下文推断得出 | 输出值，并在 `meta` 中标注推断依据 |
| 低 | 0.30 - 0.59 | 字段值存在多种可能解释 | 输出最可能值，并附 `[需核实]` 前缀 |
| 不可用 | 0 - 0.29 | 源文本中无相关信息 | 输出 `[需核实:字段名]` 占位符 |

### 降级策略

当整体置信度低于阈值（默认 0.6）时，系统将：

1. 在 `meta` 中标记 `"degraded": true`
2. 返回部分提取结果，不强行补全
3. 在输出末尾附注建议：调整提示词或补充源文本

### 自定义阈值

进阶用户可通过 `threshold` 参数调整门控阈值：

```json
{
  "text": "项目于2024年3月启动",
  "fields": ["start_date"],
  "threshold": 0.7
}
```

调高阈值可提升准确率，但会增加 `[需核实]` 占位符的出现频率；调低阈值则相反。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E1001 | 输入为空或非 UTF-8 编码 | "输入文本不能为空，且必须为 UTF-8 编码" | 检查输入编码，转换为 UTF-8 后重试 |
| E1002 | `fields` 参数格式错误 | "fields 参数必须为 JSON 数组格式" | 将 `fields` 改为 `["field1", "field2"]` 格式 |
| E1003 | 批量输入格式错误 | "批量模式要求输入为文本数组" | 将 `texts` 参数改为数组格式 |
| E1004 | 单条文本超长 | "单条文本长度不能超过 10,000 字符" | 截断文本或拆分为多条处理 |
| E1005 | 场景匹配失败 | "无法识别输入对应的技能场景" | 补充触发关键词，或直接指定 `mode` 参数 |
| E1006 | 字段提取全部失败 | "所有字段均无法从源文本中提取" | 检查源文本是否包含目标信息，或调整 `fields` 定义 |

---

## 六、FAQ 反模式

### 反模式 1：期望系统"猜"出未提及的信息

- **错误做法**：输入"帮我提取合同金额"，但源文本中根本没有金额相关描述，期望系统"合理推测"
- **正确做法**：确认源文本确实包含目标信息；若缺失，接受 `[需核实]` 占位符，并人工补充

### 反模式 2：忽略置信度标注

- **错误做法**：直接使用 `data` 中的值，不查看 `meta.confidence`
- **正确做法**：先检查置信度，对低置信度字段进行人工复核

### 反模式 3：批量处理时不做数据清洗

- **错误做法**：直接传入包含空行、特殊字符的原始文本数组，导致大量 E1001 错误
- **正确做法**：预处理数据，去除空行和非法字符，确保每条文本格式规范

### 反模式 4：频繁调整 `fields` 而不观察输出

- **错误做法**：每次提取失败就修改 `fields` 参数，不分析失败原因
- **正确做法**：先查看错误码和 `meta` 中的统计信息，定位问题根源后再调整

### 反模式 5：将本 Skill 输出直接用于关键决策

- **错误做法**：将提取结果直接用于法律、医疗等高风险场景的最终判断
- **正确做法**：将本 Skill 输出作为辅助参考，关键场景必须人工复核

---

## 七、渐进式披露

### 新手路径（5 分钟上手）

1. 阅读「一、能力边界速查卡」了解适用范围
2. 查看「二、触发方式与场景映射」确认你的需求是否匹配
3. 按「三、标准工作流」Step 1-3 完成一次简单文本提取
4. 遇到问题查阅「五、错误码体系」

### 进阶路径（深入定制）

1. 研究「四、置信度门控机制」，理解占位符与降级策略
2. 自定义 `fields` 参数，构建专属输出模板
3. 结合批量模式处理大规模数据，观察 `meta` 中的统计信息
4. 参考「六、FAQ 反模式」优化输入提示词，提升输出质量

### 专家路径（二次开发）

1. 修改 `fields` 参数定义，适配特定业务场景
2. 调整置信度阈值，平衡召回率与准确率
3. 扩展错误码体系，对接自有监控系统
4. 结合外部知识库，丰富场景匹配规则

---

## 用户协议

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的输出结果仅供参考，不构成任何形式的保证或承诺。

2. **禁止反向工程**：未经授权，不得对本 Skill 的底层逻辑、提示词结构或元数据进行反向工程、处理、篡改或二次分发。

3. **合规使用**：使用者应确保输入内容不违反法律法规，不包含侵犯第三方权益的信息。

4. **免责声明**：本 Skill 由 AI 辅助生成，可能存在未知缺陷或局限性。使用者应在关键场景中人工复核输出结果。

<!-- user-agreement-injected -->

---

## 许可证（License）

本 Skill 采用 MIT 许可证发布：

```
MIT License

Copyright (c) 2024 原创作者（自持版权）

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

---
slug: antigravity-god-mode
name: antigravity-god-mode
displayName: 数据整形 批量转换 结构化输出
description: 将任意文本输入转换为结构化结果，支持批量处理与自定义格式。
version: 1.0.0
license: MIT
source_project: original
source_url: ""
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: "DataForge Studio"
agent_created: true
trigger_words: ["数据转换", "结构化输出", "批量处理", "格式转换", "数据整形", "数据清洗", "字段映射"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# antigravity-god-mode — 数据整形与批量转换 Skill

## 一、能力边界速查卡

本 Skill 面向需要将非结构化文本（如联系人列表、日志片段、调查问卷回复）转换为统一结构化格式（表格、JSON、CSV）的用户。适用于数据分析师、运营人员、开发者在日常工作中快速整理数据。

| 能力维度 | 支持 | 不支持 |
|---------|------|--------|
| 输入类型 | 纯文本（多行）、键值对、列表式文本 | 图片、音频、PDF 扫描件 |
| 输出格式 | 表格（Markdown）、JSON、CSV、自定义模板 | 直接写入数据库、生成图表 |
| 批量处理 | 单次最多 500 条记录 | 超过 500 条需分批执行 |
| 字段映射 | 支持自定义别名映射（如"电话"→"phone"） | 自动推断语义（需显式指定） |
| 置信度标注 | 每条记录输出置信度评分 | 无 |
| 错误恢复 | 自动跳过无法解析的行并报告 | 自动修正错误数据 |

**适用对象**：需要快速整理文本数据的个人用户或小团队；不适用于需要复杂数据清洗管道或实时数据流处理的生产环境。

---

## 二、触发方式与场景映射

当你的请求中包含以下关键词或意图时，本 Skill 将被激活：

| 触发词/短语 | 典型场景 |
|------------|---------|
| "数据转换" | "帮我把这段会议记录转成表格" |
| "结构化输出" | "把这些杂乱的文本整理成 JSON" |
| "批量处理" | "我有 200 条客户信息需要统一格式" |
| "格式转换" | "把 CSV 转成 Markdown 表格" |
| "数据整形" | "把日期格式统一成 YYYY-MM-DD" |
| "字段映射" | "把'姓名'改成'name'，'手机'改成'mobile'" |
| "数据清洗" | "去掉重复项，统一空值表示" |

**大白话示例**：
- "帮我整理一下这些联系人，做成表格" → 触发数据转换
- "这段日志太乱了，能提取关键字段吗" → 触发结构化输出
- "我有 300 行数据要统一格式" → 触发批量处理

---

## 三、标准执行流程

### 前置条件

1. 输入数据为纯文本格式，每行代表一条记录（或使用空行分隔记录）。
2. 明确指定输出格式（表格/JSON/CSV）或使用默认表格格式。
3. 如需自定义字段映射，请提前说明映射规则。

### 执行步骤

**步骤 1：收集输入并确认格式**

接收用户输入文本，自动检测分隔符（逗号、制表符、竖线等）。若无法检测，默认按行分割。

```
输入示例：
张三, 13800138000, 北京
李四, 13900139000, 上海
```

**步骤 2：解析输入内容**

将每行拆分为字段。支持以下分隔符自动检测：

| 分隔符 | 示例 |
|-------|------|
| 逗号 `,` | `姓名,电话,城市` |
| 制表符 `\t` | `姓名\t电话\t城市` |
| 竖线 `\|` | `姓名\|电话\|城市` |
| 自定义 | 用户指定（如分号 `;`） |

**步骤 3：按规则处理**

- 若用户提供了字段名映射表，则按映射关系重命名字段。
- 若未提供，则自动生成字段名（`field_1`, `field_2`, ...）。
- 对每条记录计算置信度：
  - 完整解析（所有字段非空）：置信度 0.95
  - 部分字段缺失：置信度 0.70
  - 无法解析（字段数不一致）：置信度 0.40

**步骤 4：生成结果并标注置信度**

按用户指定的输出格式生成结果。每条记录附带 `confidence` 字段。

**步骤 5：输出与自查**

输出结果后，自动检查：
- 是否有字段数不一致的行被跳过？
- 是否有空值未处理？
- 是否所有字段名符合输出格式要求？

**步骤 6：二次确认（仅在必要时）**

当置信度低于 0.50 的记录占比超过 20% 时，主动询问用户是否需要人工复核。

### 输出规范

- 表格格式：Markdown 表格，首行为字段名，末列为置信度。
- JSON 格式：数组对象，每个对象包含 `data` 和 `confidence` 两个键。
- CSV 格式：首行为字段名，末列为置信度，使用逗号分隔。

---

## 四、置信度门控机制

本 Skill 遵循"不编造"原则。当遇到以下情况时，使用占位符 `[需核实:字段名]` 代替猜测值：

| 情况 | 处理方式 |
|------|---------|
| 字段缺失 | 填入 `[需核实:字段名]`，置信度降至 0.70 |
| 字段格式异常（如日期格式错误） | 保留原值，标注 `[需核实:字段名]`，置信度降至 0.60 |
| 整行无法解析 | 跳过该行，在输出末尾列出被跳过的行号 |

**输出末尾追加提示**：
> 注意：以下字段需人工核实：[字段名列表]

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|-------|------|---------|---------|
| E001 | 输入为空 | "未检测到输入数据，请提供至少一行文本。" | 检查输入是否为空，重新提交 |
| E002 | 分隔符无法识别 | "无法自动检测分隔符，请指定分隔符（如逗号、制表符）。" | 在输入中明确分隔符类型 |
| E003 | 字段数不一致 | "第 N 行字段数与其他行不一致，已跳过。" | 检查该行数据，补齐缺失字段 |
| E004 | 输出格式不支持 | "仅支持表格、JSON、CSV 三种格式。" | 重新指定输出格式 |
| E005 | 批量处理超限 | "单次最多处理 500 条记录，当前为 N 条。" | 将数据分批处理 |
| E006 | 字段映射冲突 | "映射规则中'X'同时映射到多个目标字段。" | 检查映射表，确保一对一映射 |
| E007 | 置信度过低 | "超过 20% 的记录置信度低于 0.50，建议人工复核。" | 检查原始数据质量，或手动修正 |

---

## 六、FAQ 与反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|-------|------------------|---------|
| 输入格式混乱 | 直接提交未整理的原始文本，期望自动修复 | 先手动清理明显错误，再提交 |
| 字段名冲突 | 映射表中多个源字段映射到同一目标字段 | 检查映射表，确保唯一性 |
| 忽略置信度 | 直接使用低置信度结果而不复核 | 对置信度低于 0.70 的记录进行人工检查 |
| 批量处理超限 | 一次性提交 1000 条记录 | 分批处理，每批不超过 500 条 |
| 自定义模板错误 | 模板中引用了不存在的字段名 | 核对模板字段名与输出字段名一致 |

---

## 七、渐进式阅读路径

### 新手入门（5 分钟上手）

1. 阅读「能力边界速查卡」了解能做什么。
2. 准备一份简单的文本输入（如几条联系人信息）。
3. 指定输出格式为"表格"。
4. 执行流程，观察输出结构。
5. 遇到问题对照「错误码体系」排查。

### 进阶使用（提升效率）

1. 掌握自定义字段映射规则（如"将'电话'映射为 phone"）。
2. 使用批量处理处理大量数据，注意错误码 E006 的处理。
3. 结合置信度门控，对低置信度结果进行人工复核。
4. 自定义输出模板，固定字段顺序与格式。

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用前请仔细阅读以下条款，使用本 Skill 即视为同意本协议：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的输出结果仅供参考，不构成任何形式的保证或承诺。

2. **禁止反向工程**：使用者不得对本 Skill 的底层逻辑、提示词结构、评分机制进行反向工程、破解、篡改或二次分发。

3. **合规使用**：使用者应确保输入数据来源合法，不得使用本 Skill 处理违法违规内容。

4. **免责声明**：本 Skill 由 AI 辅助生成，仅供学习参考。因使用本 Skill 导致的任何直接或间接损失，作者不承担任何责任。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 DataForge Studio

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

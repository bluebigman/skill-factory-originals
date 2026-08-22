---
slug: nima0011
name: nima0011
displayName: 数据解析 结构化转换 置信度标注
description: 将用户提供的数据、文件或URL转换为结构化结果，并标注置信度。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林默
agent_created: true
trigger_words: ["nima0011", "数据转换", "结构化输出", "信息提取", "批量处理", "格式转换"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# Skill：数据解析与结构化转换

## 一、能力边界（一页纸速查卡）

### 1.1 能做（核心能力）

| 编号 | 能力项 | 说明 | 适用场景示例 |
|------|--------|------|--------------|
| C1 | 数据/文件/URL 解析 | 从用户提供的文本、文件（CSV/JSON/TXT）或网页 URL 中提取内容 | 读取一份 CSV 文件并转为结构化条目 |
| C2 | 关键信息识别与保留 | 自动识别输入中的核心字段（如 ID、名称、日期、数值）并保留 | 从日志中提取时间戳与错误码 |
| C3 | 约定格式输出 | 按用户指定的字段结构或默认模板生成输出 | 将散乱数据整理为表格或 JSON |
| C4 | 置信度标注 | 对每个输出字段标注可信程度（高/中/低） | 识别结果存在歧义时给出提示 |
| C5 | 批量处理与自定义格式 | 支持多文件/多条目批量执行，允许用户自定义输出模板 | 一次处理 100 条记录并导出为指定格式 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行外部系统写入 | 本 Skill 仅做解析与转换，不向数据库、API 或第三方平台写入数据 |
| L2 | 不处理加密或二进制文件 | 仅支持明文文本类格式（TXT/CSV/JSON/MD），不支持 PDF 扫描件、加密压缩包 |
| L3 | 不进行语义推理 | 不判断信息"对错"，只做提取与结构化；涉及主观判断时需用户确认 |
| L4 | 不保证 100% 准确 | 所有输出均带置信度标注，低置信度字段需用户复核 |

### 1.3 适用对象

- **输入**：用户提供的文本片段、本地文件路径（需在同一目录）、可公开访问的 URL
- **输出**：Markdown 表格、JSON 对象、CSV 行（用户三选一）
- **前置条件**：文件命名规范一致（建议 `input_*.csv` 格式），URL 可正常访问

---

## 二、触发方式

### 2.1 触发词

- 主触发词：`nima0011`
- 同义触发词：`数据转换`、`结构化输出`、`信息提取`、`批量处理`、`格式转换`

### 2.2 场景映射表

| 用户说（大白话） | 实际触发动作 |
|------------------|--------------|
| "帮我把这个文件整理一下" | 解析文件 → 识别关键字段 → 输出结构化表格 |
| "这个 URL 里的数据能提取出来吗" | 抓取 URL 内容 → 提取关键信息 → 标注置信度 |
| "我有 50 条记录要转成 JSON" | 批量解析 → 按 JSON 模板输出 |
| "这堆数据里哪些是重要的？" | 识别关键字段 → 保留核心信息 → 丢弃噪声 |

---

## 三、标准流程

### 3.1 前置条件检查

| 检查项 | 要求 | 不满足时的处理 |
|--------|------|----------------|
| 输入来源 | 文本/文件/URL 三者至少其一 | 提示用户提供输入 |
| 文件命名 | 同一目录下命名规范一致 | 建议用户重命名后重试 |
| 输出格式 | 用户指定或默认 Markdown 表格 | 默认采用 Markdown 表格 |
| 数据量级 | 单次不超过 500 条记录 | 超出时建议分批处理 |

### 3.2 执行步骤（分步编号）

1. **接收输入**：确认输入类型（文本/文件/URL），读取原始内容。
2. **内容解析**：
   - 若为文件：按扩展名识别格式（CSV 按逗号分隔，JSON 按键值对解析，TXT 按行读取）。
   - 若为 URL：抓取页面文本内容，去除 HTML 标签。
   - 若为纯文本：按换行符或用户指定的分隔符切分。
3. **关键信息识别**：
   - 扫描内容中的数字、日期（YYYY-MM-DD）、邮箱、ID 等模式。
   - 保留用户明确指定的字段；未指定时自动提取高频出现的关键词。
4. **结构化处理**：
   - 将每条记录映射到统一字段结构（默认字段：`id`, `name`, `value`, `timestamp`）。
   - 对缺失字段填充 `null`，并在置信度中标记为"低"。
5. **置信度标注**：
   - **高**：字段值完整且无歧义（如纯数字 ID）。
   - **中**：字段值存在多种可能解释（如名称缩写）。
   - **低**：字段缺失或来源不可靠（如 URL 内容不完整）。
6. **输出生成**：
   - 按用户选择的格式（Markdown/JSON/CSV）生成结果。
   - 在输出末尾附置信度汇总表。

### 3.3 输出规范

**默认 Markdown 表格示例：**

| id | name | value | timestamp | 置信度 |
|----|------|-------|-----------|--------|
| 001 | 项目A | 42 | 2025-01-15 | 高 |
| 002 | 项目B | null | 2025-01-16 | 低（value 缺失） |

**JSON 输出示例：**

```json
[
  {
    "id": "001",
    "name": "项目A",
    "value": 42,
    "timestamp": "2025-01-15",
    "confidence": {"value": "high", "note": ""}
  }
]
```

---

## 四、置信度门控

### 4.1 门控规则

- 当输入信息不足以确定某字段值时，**禁止编造**，输出 `[需核实:字段名]` 占位符。
- 占位符格式：`[需核实:timestamp]`，并在置信度列标注"低"。
- 若超过 30% 的字段为低置信度，输出末尾追加提示："建议人工复核后使用"。

### 4.2 示例

**输入**："2025年3月 项目X 完成 50%"

**输出**：

| id | name | value | timestamp | 置信度 |
|----|------|-------|-----------|--------|
| [需核实:id] | 项目X | 50% | 2025-03 | 中（id 缺失，timestamp 不完整） |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 输入为空 | "未检测到有效输入，请提供文本、文件路径或 URL。" | 重新提供输入 |
| E002 | 文件不存在 | "指定路径下未找到文件，请确认文件名与目录。" | 检查路径，重试 |
| E003 | 格式不支持 | "当前文件格式不支持，仅支持 TXT/CSV/JSON。" | 转换格式后重试 |
| E004 | URL 无法访问 | "URL 返回 404 或超时，请确认链接有效性。" | 更换 URL 或手动粘贴内容 |
| E005 | 字段冲突 | "输入中同一字段存在多个值，无法自动判定。" | 指定优先级或手动选择 |
| E006 | 超出批量限制 | "单次处理上限为 500 条，当前超出。" | 拆分批次执行 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|--------------------|----------|
| 忽略置信度 | 直接使用低置信度数据做决策 | 先复核低置信度字段 |
| 过度依赖自动识别 | 完全信任自动提取的字段名 | 对照原始输入抽查 10% 条目 |
| 不保留原始文件 | 批量处理后删除源文件 | 保留备份，便于追溯 |
| 跳过试运行 | 直接全量执行 | 先用单样本验证输出格式 |
| 自定义格式不校验 | 输出后不检查字段完整性 | 使用 `--selftest` 校验模板 |

### 6.2 反模式示例

- **错误**：用户提供 200 条记录，直接全量转换，结果发现日期格式全错。
- **正确**：先取 1 条试运行，确认日期格式为 `YYYY-MM-DD` 后再批量执行。

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

1. 把文件放到当前目录，命名 `input_*.csv`。
2. 输入：`nima0011 处理 input_001.csv`。
3. 指定输出格式：`输出为 JSON`。
4. 检查置信度列，低置信度字段手动确认。

### 7.2 新手路径（首次使用）

- 阅读「能力边界」→ 确认输入类型 → 按「标准流程」执行 → 查看输出与置信度。
- 遇到错误码时，对照「错误码体系」表格处理。

### 7.3 进阶路径（熟练用户）

- 自定义输出模板：在输入中附加 `模板: {"字段1": "类型"}`。
- 批量处理：使用 `批量: 目录路径` 一次处理多文件。
- 校验模式：使用 `--selftest` 检查输出模板完整性。

---

## 八、CLI 接口说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `--selftest` | 运行自检，验证输出模板与字段完整性 | `nima0011 --selftest` |
| `--version` | 显示版本号 | `nima0011 --version` |

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担全部责任。本 Skill 提供的输出仅供参考，不构成任何形式的专业建议或决策依据。
2. **禁止反向工程**：不得对本 Skill 的底层逻辑、代码结构进行反向工程、反编译或试图提取源代码。
3. **合规使用**：使用者应确保输入数据来源合法，不得使用本 Skill 处理违反法律法规的内容。
4. **无担保**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 许可证（License）

本 Skill 采用 MIT 许可证发布。

```
MIT License

Copyright (c) 2025 林默

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

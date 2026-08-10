---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agent-resources
name: agent-resources
displayName: 资源采集 数据转换 批量处理
description: 将任意数据、文件或URL转换为结构化结果，支持批量处理与自定义格式。
version: 2.0.1
rules_version: cpr-20260810-n301
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agent-resources
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 流云架构师
agent_created: true
trigger_words: ["agent-resources", "资源转换", "数据采集", "结构化输出", "批量处理", "数据清洗", "格式转换"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# agent-resources Skill 使用指南

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 数据采集 | 从 URL、本地文件、原始文本中提取信息 | 抓取网页标题、读取 CSV 文件内容 |
| 格式转换 | 将非结构化数据转为 JSON / Markdown / 自定义模板 | 将日志文本转为 JSON 数组 |
| 批量处理 | 对多个输入源执行同一套转换逻辑 | 一次处理 50 个 URL 的标题提取 |
| 自定义输出 | 按用户指定的字段结构输出结果 | 只输出 `{url, title, timestamp}` 三个字段 |
| 数据清洗 | 去除空白、去重、过滤无效记录 | 删除空行、合并重复条目 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行代码 | 本 Skill 只做数据转换，不运行用户提供的脚本 |
| 不访问登录态内容 | 需要 Cookie / Token 的页面无法抓取 |
| 不处理二进制大文件 | 超过 50MB 的文件建议先拆分 |
| 不保证数据准确性 | 源数据本身有误时，转换结果同样有误 |
| 不进行语义理解 | 只做结构化处理，不判断内容含义对错 |

### 1.3 适用对象

- 需要将散乱数据整理为固定格式的开发者
- 需要批量抓取网页标题、描述、链接的内容运营人员
- 需要将 CSV / TXT / JSON 互转的数据分析初学者
- 需要为下游程序准备干净输入数据的自动化流程设计者

---

## 二、触发方式：场景映射表

| 触发词 | 大白话场景 | 本 Skill 会做什么 |
|--------|------------|-------------------|
| "把这段文本转成 JSON" | 你有一段非结构化文本，想变成键值对 | 解析文本，按行/分隔符提取字段，输出 JSON |
| "批量提取这些 URL 的标题" | 你有 10 个网址，想一次性拿到每个页面的标题 | 逐个请求 URL，提取 `<title>` 标签，汇总为数组 |
| "把这个 CSV 转成 Markdown 表格" | 你有一个表格文件，想在文档里展示 | 读取 CSV，生成 Markdown 表格语法 |
| "清洗这份数据" | 数据里有空行、重复项、多余空格 | 过滤空值、去重、trim 字符串，输出干净版本 |
| "按我的模板输出" | 你希望结果只包含指定字段 | 根据你提供的字段列表，裁剪输出结构 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 输入数据 | 文本、URL、CSV、JSON 文件路径 | 确认文件存在且可读 |
| 输出格式 | 明确指定 JSON / Markdown / 自定义模板 | 用户需在请求中说明 |
| 批量数量 | 单次不超过 100 个输入项 | 超过则建议分批 |
| 网络权限 | 抓取 URL 时需能访问外网 | 本地测试可跳过 |

### 3.2 执行步骤

1. **确认输入类型**：判断输入是 URL、文件路径、还是直接粘贴的文本。
2. **确认输出格式**：询问用户期望的格式（默认 JSON）。
3. **执行转换**：
   - 若为 URL：发起 HTTP 请求 → 解析 HTML → 提取指定字段。
   - 若为文件：读取文件 → 按扩展名选择解析器（CSV 用逗号分隔，JSON 直接解析）。
   - 若为文本：按行拆分 → 识别分隔符（逗号、制表符、竖线）→ 映射为字段。
4. **清洗数据**：去除首尾空白、过滤空行、合并重复项（可选，默认开启）。
5. **格式化输出**：按用户指定格式生成结果。
6. **返回结果**：输出结构化数据，附处理统计（输入条数、输出条数、丢弃条数）。

### 3.3 输出规范

```json
{
  "status": "success",
  "input_count": 12,
  "output_count": 10,
  "dropped_count": 2,
  "data": [
    { "field1": "value1", "field2": "value2" }
  ]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 是 | `success` 或 `error` |
| input_count | int | 是 | 接收到的输入条目数 |
| output_count | int | 是 | 成功转换的条目数 |
| dropped_count | int | 是 | 因格式错误/空值丢弃的条目数 |
| data | array | 是 | 转换后的结构化数据 |

---

## 四、置信度门控

当遇到以下情况时，**不猜测、不编造**，直接输出占位符：

| 场景 | 处理方式 |
|------|----------|
| 字段值缺失 | 输出 `[需核实:字段名]` |
| 无法解析的格式 | 输出 `[需核实:原始内容]` 并保留原文 |
| URL 请求失败 | 输出 `[需核实:URL状态码]`，跳过该条 |
| 编码无法识别 | 输出 `[需核实:文件编码]`，尝试 UTF-8 解码 |

示例：

```json
{
  "status": "success",
  "data": [
    { "title": "产品发布公告", "author": "[需核实:作者]" }
  ]
}
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| AR-001 | 输入为空 | "未检测到输入数据，请提供文本、文件路径或 URL" | 检查输入是否为空，重新提交 |
| AR-002 | 文件不存在 | "指定路径下未找到文件，请确认路径是否正确" | 核对路径，使用绝对路径 |
| AR-003 | URL 无法访问 | "目标 URL 返回 404 或超时，请检查链接有效性" | 手动打开 URL 验证，或更换链接 |
| AR-004 | 格式无法识别 | "无法自动识别输入格式，请指定分隔符或格式类型" | 明确告知分隔符（如逗号、制表符） |
| AR-005 | 批量超限 | "单次批量处理上限为 100 条，当前超出限制" | 将输入拆分为多批，逐批处理 |
| AR-006 | 输出格式不支持 | "仅支持 JSON、Markdown、CSV 三种输出格式" | 重新指定输出格式 |

---

## 六、FAQ 反模式

### 反模式 1：直接抓取整个网页内容

**错误做法**：请求 URL 后，将整个 HTML 原文作为结果输出。

**正确做法**：明确提取目标字段（标题、描述、链接），只输出结构化字段。

### 反模式 2：忽略编码问题

**错误做法**：遇到乱码直接丢弃该条数据。

**正确做法**：尝试多种编码（UTF-8 → GBK → Latin-1），仍失败则输出 `[需核实:文件编码]`。

### 反模式 3：静默丢弃异常数据

**错误做法**：转换失败的数据不提示，直接减少输出条数。

**正确做法**：在 `dropped_count` 中统计，并在 `data` 末尾附上原始异常内容（带占位符）。

### 反模式 4：对空值强行赋值

**错误做法**：字段为空时填入 `"未知"` 或 `"N/A"`。

**正确做法**：保留 `[需核实:字段名]`，让用户自行决定是否填充。

### 反模式 5：批量处理时不做进度反馈

**错误做法**：100 条数据一次性处理完才返回，用户等待无反馈。

**正确做法**：分批返回（每 20 条一组），或返回处理进度百分比。

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

1. 输入：文本 / 文件路径 / URL
2. 输出：JSON / Markdown / CSV
3. 默认清洗：去空白、去空行、去重
4. 批量上限：100 条/次
5. 出错不编造：用 `[需核实:字段]` 占位

### 7.2 进阶路径（有经验用户）

**第一层：基础转换**
- 掌握输入类型判断逻辑
- 熟悉三种输出格式的差异

**第二层：批量与清洗**
- 理解 `dropped_count` 的统计规则
- 学会自定义清洗规则（如保留特定字段）

**第三层：自定义模板**
- 使用字段映射语法：`{"目标字段": "源字段"}`
- 支持嵌套结构：`{"user": {"name": "username"}}`

**第四层：错误处理策略**
- 针对 AR-003（URL 失败），可配置重试次数（默认 2 次）
- 针对 AR-004（格式不明），可预设分隔符优先级

---

## 八、参数速查表

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `input_type` | string | auto | `url` / `file` / `text` / `auto` |
| `output_format` | string | json | `json` / `markdown` / `csv` |
| `delimiter` | string | auto | 文本分隔符，`auto` 自动检测 |
| `clean` | bool | true | 是否执行清洗（去空白/去空行/去重） |
| `fields` | array | [] | 自定义输出字段列表，空则输出全部 |
| `batch_size` | int | 20 | 批量处理时每批条数 |
| `retry_count` | int | 2 | URL 请求失败重试次数 |
| `timeout` | int | 10 | URL 请求超时时间（秒） |

---

## 九、完整示例

### 示例 1：文本转 JSON

**输入**：
```
name,age,city
张三,28,北京
李四,35,上海
```

**请求**：`将以下文本转为 JSON，字段为 name/age/city`

**输出**：
```json
{
  "status": "success",
  "input_count": 3,
  "output_count": 3,
  "dropped_count": 0,
  "data": [
    { "name": "张三", "age": "28", "city": "北京" },
    { "name": "李四", "age": "35", "city": "上海" }
  ]
}
```

### 示例 2：URL 批量提取标题

**输入**：`["https://example.com/a", "https://example.com/b"]`

**请求**：`提取这些 URL 的标题`

**输出**：
```json
{
  "status": "success",
  "input_count": 2,
  "output_count": 2,
  "dropped_count": 0,
  "data": [
    { "url": "https://example.com/a", "title": "页面 A 标题" },
    { "url": "https://example.com/b", "title": "页面 B 标题" }
  ]
}
```

---

## 用户协议

<!-- user-agreement-injected -->

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于数据准确性、合规性、以及因错误使用导致的任何损失。
2. **禁止反向工程**：不得对本 Skill 的底层逻辑进行逆向工程、反编译、或试图提取源代码。
3. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性。
4. **数据安全**：使用者需自行确保输入数据的合法性与安全性，本 Skill 不承担数据泄露或丢失的责任。
5. **修改与终止**：作者保留随时修改、更新或终止本 Skill 的权利，恕不另行通知。

---

## 许可证（License）

<!-- professional-license-embedded -->

MIT License

Copyright (c) 2026 流云架构师

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

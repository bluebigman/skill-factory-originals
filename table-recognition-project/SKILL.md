---
slug: table-recognition-project
name: table-recognition-project
displayName: 表格识别 数据清洗 结构化输出
description: 将表格类数据或文件解析为结构化结果，提供规范处理流程与置信度标注。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataFlow Studio
agent_created: true
trigger_words: ["Excel 数据处理", "table recognition project", "表格识别", "结构化输出", "数据解析"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# 表格识别与结构化输出 Skill 文档

## 一、能力边界速查卡

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|--------|----------|
| 输入类型 | 用户提供的表格文件（xlsx/csv/tsv）、文本数据、可访问的 URL 指向的表格 | 扫描件/图片中的表格（OCR 不在本 Skill 范围内） |
| 处理能力 | 解析行列结构、识别表头、字段映射、类型推断、批量处理 | 对模糊图片做视觉识别、跨表关联查询、数据修复 |
| 输出形式 | 结构化 JSON/CSV、按约定字段重排、自定义模板输出 | 生成可视化图表、自动写入外部数据库 |
| 质量保障 | 对不确定字段标注置信度、输出 `[需核实:字段名]` 占位 | 对缺失数据凭空补值、保证 100% 准确率 |
| 交互方式 | 单文件处理、批量目录处理、自定义格式参数 | 实时流式处理、分布式计算 |

### 1.2 适用对象

- **数据分析师**：需要快速将杂乱的表格数据转为统一格式。
- **业务运营人员**：定期整理导出报表，需要标准化命名与字段。
- **开发人员**：需要将表格数据接入下游系统，要求字段结构稳定。

---

## 二、触发方式与场景映射

当你的需求符合以下任一场景时，即可使用本 Skill：

| 大白话描述 | 触发关键词示例 | 本 Skill 动作 |
|-----------|---------------|---------------|
| "帮我把这个 Excel 里的数据整理成统一的格式" | Excel 数据处理、表格整理 | 解析文件 → 字段映射 → 输出结构化结果 |
| "这个 CSV 文件列名太乱，帮我规范化" | 表格识别、字段规范化 | 识别表头 → 重命名映射 → 输出标准字段 |
| "我需要把网页上的表格抓下来变成 JSON" | URL 表格解析、结构化输出 | 拉取 URL → 提取表格 → 转为 JSON |
| "这批文件格式都一样，帮我批量处理" | 批量处理、批量转换 | 遍历目录 → 逐文件执行 → 汇总输出 |

---

## 三、标准处理流程

### 3.1 前置条件

| 条件项 | 要求 |
|--------|------|
| 文件格式 | `.xlsx` / `.xls` / `.csv` / `.tsv`，编码建议 UTF-8 |
| 文件命名 | 建议使用 `项目名_日期_序号` 格式，避免特殊字符 |
| 目录结构 | 待处理文件放入同一目录，原始文件保留备份 |
| 环境依赖 | Python 3.8+，安装 `pandas` / `openpyxl`（如适用） |

### 3.2 执行步骤（分步编号）

1. **准备输入**：将待处理文件放入同一目录，确认命名规范一致。若为 URL，确认链接可公开访问且返回 HTML 表格。
2. **试运行**：先用单个样本执行，核对输出字段与格式是否符合预期。
3. **批量执行**：确认无误后对全量数据执行，并保留原始文件备份。
4. **校验结果**：抽查输出条目，核对关键字段与源数据一致。

### 3.3 输出规范

输出文件默认采用以下结构（可通过参数自定义）：

```json
{
  "schema_version": "1.0",
  "generated_at": "2025-01-01T12:00:00Z",
  "record_count": 123,
  "records": [
    {
      "id": 1,
      "fields": {
        "field_a": "value",
        "field_b": 42
      },
      "confidence": 0.95,
      "warnings": []
    }
  ]
}
```

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `schema_version` | string | 输出格式版本号，固定为 `1.0` |
| `generated_at` | string | ISO 8601 时间戳，记录生成时间 |
| `record_count` | int | 记录总数 |
| `records[].id` | int | 行号，从 1 开始 |
| `records[].fields` | object | 字段名与值的映射 |
| `records[].confidence` | float | 0~1 之间的置信度评分 |
| `records[].warnings` | array | 该行的警告信息列表 |

---

## 四、置信度门控机制

当遇到以下情况时，**不得编造数据**，必须按规则处理：

| 场景 | 处理方式 |
|------|----------|
| 字段值为空 | 输出 `null`，置信度降为 0.5，warnings 添加 `"empty_field: 字段名"` |
| 字段类型无法推断 | 输出 `[需核实:字段名]` 占位符，置信度降为 0.3 |
| 表头映射不确定（多个候选列名） | 输出 `[需核实:字段名]`，warnings 添加 `"ambiguous_header: 候选列名列表"` |
| 数据格式异常（如日期格式不统一） | 保留原始值，warnings 添加 `"format_inconsistency: 字段名"` |

**置信度计算规则：**

- 基础分 1.0，每出现一个 warning 扣 0.2，最低不低于 0.1。
- 若存在 `[需核实:...]` 占位符，置信度上限为 0.5。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件不存在或路径错误 | "未找到指定文件，请检查路径是否正确" | 确认文件路径，重新输入 |
| `E002` | 文件格式不支持 | "仅支持 xlsx/csv/tsv 格式，请转换后重试" | 使用 Excel 或脚本转换格式 |
| `E003` | 表格无有效表头 | "未检测到表头行，请确认首行是否为列名" | 手动添加表头行，或指定 `header_row` 参数 |
| `E004` | 字段映射失败 | "存在无法映射的字段，请检查列名拼写" | 查看 warnings 详情，补充映射规则 |
| `E005` | URL 无法访问 | "URL 返回非 200 状态码，请确认链接有效性" | 检查网络或更换可访问链接 |
| `E006` | 批量处理中断 | "第 N 个文件处理失败，已跳过并记录日志" | 查看错误日志，修复后重跑失败项 |

---

## 六、FAQ 反模式对照

| 常见坑（反模式） | 正确做法（正模式） |
|-----------------|-------------------|
| 直接对全量数据执行，不做试运行 | 先用单个样本验证输出格式，再批量执行 |
| 发现字段缺失时自行猜测补值 | 使用 `[需核实:字段名]` 占位，交由用户确认 |
| 忽略 warnings，只看主数据 | 每次输出后检查 warnings 列表，逐条确认 |
| 修改原始文件后再处理 | 始终保留原始文件备份，处理副本 |
| 认为置信度 1.0 就是绝对正确 | 置信度仅反映内部一致性，不代表业务正确性 |

---

## 七、渐进式阅读路径

### 7.1 新手路径（5 分钟上手）

1. 阅读「一、能力边界速查卡」了解适用范围。
2. 对照「二、触发方式与场景映射」确认你的需求匹配。
3. 按「三、标准处理流程」的步骤 1-2 完成一次单文件试运行。
4. 查看输出 JSON 中的 `confidence` 和 `warnings` 字段。

### 7.2 进阶路径（深入使用）

1. 阅读「四、置信度门控机制」理解不确定项的处理逻辑。
2. 对照「五、错误码体系」排查运行中的报错。
3. 阅读「六、FAQ 反模式对照」避免常见操作失误。
4. 自定义输出模板：在调用时传入 `output_template` 参数，指定字段顺序与重命名规则。

---

## 八、参数速查表

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `input_path` | string | 无（必填） | 文件路径或 URL |
| `output_path` | string | `./output.json` | 输出文件路径 |
| `header_row` | int | 1 | 表头所在行号（从 1 开始） |
| `encoding` | string | `utf-8` | 文件编码 |
| `field_mapping` | dict | `{}` | 自定义字段映射，如 `{"原列名": "标准字段名"}` |
| `batch_mode` | bool | `false` | 是否批量处理目录下所有匹配文件 |
| `output_template` | string | `json` | 输出格式，可选 `json` / `csv` |

---

## 九、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的输出结果仅供参考，不构成任何形式的专业建议或保证。
2. **禁止反向工程**：不得对本 Skill 的底层逻辑进行反向工程、反编译或试图提取源代码（除非适用法律允许）。
3. **数据安全**：使用者应确保输入数据不包含敏感个人信息或受保护数据。因数据泄露或误用产生的后果由使用者自行承担。
4. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

本 Skill 采用 MIT 许可证发布。

```
MIT License

Copyright (c) 2025 DataFlow Studio

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

*文档版本：1.0.0 | 最后更新：2025-01-01*

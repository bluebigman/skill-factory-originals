---
slug: excel-image-extractor
name: excel-image-extractor
displayName: 表格图片 数据抽取 结构化输出
description: 从Excel与图片中抽取关键数据，按约定格式输出结构化结果。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataPilot Studio
agent_created: true
trigger_words: ["Excel表格处理", "excel image extractor", "表格数据抽取", "图片转表格", "表格结构化", "表格识别", "数据提取"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# Excel 图片数据抽取 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| Excel 表格抽取 | 从 `.xlsx` / `.xls` 文件中读取指定工作表，提取关键字段 | 读取销售明细表中的订单号、金额、日期 |
| 图片表格识别 | 对包含表格结构的图片（`.png` / `.jpg`）进行 OCR 识别并结构化 | 扫描发票照片，提取发票号码、税额 |
| 批量处理 | 对同一目录下的多个文件按统一规则批量抽取 | 处理 50 张月度报表截图 |
| 格式标准化 | 将抽取结果统一为 JSON / CSV 格式输出 | 输出 `[{ "字段A": "值1" }]` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 复杂版式还原 | 无法还原合并单元格、斜线表头等复杂版式的原始视觉结构 |
| 手写体识别 | 对手写数字/文字识别准确率较低，需人工复核 |
| 语义理解 | 不推断字段含义，仅按用户指定的字段名抽取对应位置数据 |
| 公式计算 | 不执行 Excel 公式运算，只读取单元格的显示值或公式文本 |

### 1.3 适用对象

- 需要从批量报表中提取关键指标的运营人员
- 需要将纸质/图片表格数字化的行政或财务人员
- 需要将异构表格统一为结构化数据的数据工程师

---

## 二、触发方式

### 2.1 触发词

当用户输入包含以下任一关键词时，本 Skill 自动激活：

- `Excel表格处理`
- `excel image extractor`
- `表格数据抽取`
- `图片转表格`
- `表格结构化`
- `表格识别`
- `数据提取`

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 触发动作 |
|------------------|----------|----------|
| "帮我把这张发票图片里的金额和税号弄出来" | 图片表格抽取 | 执行图片识别 + 字段提取 |
| "这个 Excel 里有很多表，我只想要每个 sheet 的第一行和合计行" | 指定范围抽取 | 按 sheet 遍历 + 定位行提取 |
| "我这有 100 个文件，格式都一样，帮我全跑一遍" | 批量处理 | 目录遍历 + 统一规则抽取 |
| "抽出来的数据要能直接导入数据库" | 格式标准化 | 输出 JSON / CSV 并校验字段类型 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| 文件目录 | 所有待处理文件放在同一目录下，路径中不含中文或空格（建议） |
| 命名规范 | 文件名前缀一致，例如 `report_202401.xlsx`、`invoice_001.png` |
| 字段定义 | 用户需明确指定要抽取的字段名（如 `订单号`、`金额`、`日期`） |
| 环境依赖 | Python 3.9+，已安装 `pandas`、`openpyxl`、`pytesseract`（图片识别） |

### 3.2 执行步骤

#### 步骤 1：准备输入

```bash
# 将文件放入 ./input 目录
mkdir -p input output
cp /path/to/files/*.xlsx ./input/
cp /path/to/images/*.png ./input/
```

#### 步骤 2：单样本试运行

```python
# 示例：抽取单个 Excel 文件
from excel_image_extractor import extract_from_excel

result = extract_from_excel(
    file_path="./input/report_202401.xlsx",
    sheet_name="Sheet1",
    fields=["订单号", "金额", "日期"]
)
print(result)
```

**核对要点**：
- 输出字段名是否与预期一致
- 数据类型是否正确（金额为数字，日期为日期格式）
- 空值是否以 `null` 或 `""` 表示

#### 步骤 3：批量执行

```python
# 批量处理目录下所有 .xlsx 文件
from excel_image_extractor import batch_extract

results = batch_extract(
    input_dir="./input",
    output_dir="./output",
    file_pattern="*.xlsx",
    fields=["订单号", "金额", "日期"]
)
```

**注意**：执行前备份原始文件到 `./backup` 目录，防止误操作。

#### 步骤 4：校验结果

- 随机抽取 5% 的条目，人工核对源文件与输出是否一致
- 检查字段完整性：是否存在缺失字段（应显示 `[需核实:字段名]`）
- 检查数值精度：金额保留两位小数，日期格式统一为 `YYYY-MM-DD`

### 3.3 输出规范

| 输出格式 | 适用场景 | 示例 |
|----------|----------|------|
| JSON | API 对接、数据库导入 | `[{"订单号": "A001", "金额": 100.50}]` |
| CSV | Excel 打开、报表分析 | `订单号,金额\nA001,100.50` |

**字段类型约定**：

| 字段类型 | 输出格式 | 示例 |
|----------|----------|------|
| 字符串 | 原样输出 | `"张三"` |
| 数字 | 浮点数（保留两位） | `100.50` |
| 日期 | `YYYY-MM-DD` | `2024-01-15` |
| 空值 | `null`（JSON）/ 空（CSV） | `null` |

---

## 四、置信度门控

当抽取过程中出现以下情况时，**不得编造数据**，必须输出占位符：

| 情况 | 输出占位符 | 说明 |
|------|------------|------|
| 单元格为空 | `[需核实:字段名]` | 该字段在源文件中无值 |
| 图片模糊无法识别 | `[需核实:字段名]` | OCR 置信度低于 60% |
| 字段名不匹配 | `[需核实:字段名]` | 源文件中找不到用户指定的字段 |
| 日期格式异常 | `[需核实:日期]` | 无法解析为合法日期 |

**示例输出**：

```json
[
  {
    "订单号": "A001",
    "金额": 100.50,
    "日期": "[需核实:日期]"
  }
]
```

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `E001` | 文件不存在 | "未找到指定文件，请检查路径" | 确认文件路径是否正确，文件是否已放入 `./input` 目录 |
| `E002` | 工作表不存在 | "指定的 Sheet 不存在，请确认名称" | 列出所有 sheet 名，选择正确的名称 |
| `E003` | 字段名不匹配 | "源文件中未找到字段：{字段名}" | 检查源文件表头，调整字段名拼写 |
| `E004` | 图片 OCR 失败 | "图片识别失败，请检查图片清晰度" | 重新拍摄或扫描，确保表格线清晰、无阴影 |
| `E005` | 批量处理中断 | "批量处理在第 {n} 个文件时中断" | 查看日志定位失败文件，单独处理该文件 |
| `E006` | 输出目录不可写 | "无法写入输出目录，请检查权限" | 修改目录权限或更换输出路径 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式（错误做法） | 正确做法 |
|----|-------------------|----------|
| 忽略空值 | 将空单元格填为 `0` 或 `"无"` | 保留 `null` 或 `[需核实:字段名]`，由下游决定处理策略 |
| 盲目批量 | 不试运行直接全量执行 | 先用单个样本验证规则，再批量执行 |
| 覆盖原始文件 | 直接在原文件上修改 | 始终保留备份，输出到独立目录 |
| 忽略日期格式 | 直接输出 Excel 序列号（如 45292） | 转换为 `YYYY-MM-DD` 格式 |
| 字段名硬编码 | 在代码中写死字段名，不校验 | 每次执行前动态读取表头，校验字段存在性 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| "这个字段肯定有值，直接填 0" | 掩盖数据缺失，导致统计偏差 | 输出 `[需核实:字段名]`，人工确认 |
| "所有文件格式都一样，不用试跑" | 个别文件表头偏移导致全批失败 | 抽样 3 个文件试运行，确认后再全量 |
| "图片看不清就猜一个值" | 编造数据，不可追溯 | 输出 `[需核实:字段名]`，标记为待人工处理 |
| "直接覆盖原文件，省事" | 数据丢失不可恢复 | 备份到 `./backup`，输出到 `./output` |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

1. 把文件放到 `./input`
2. 运行单样本抽取，核对字段
3. 批量执行，输出到 `./output`
4. 抽查 5% 结果，确认无误

### 7.2 新手路径（首次使用）

- 阅读「能力边界」了解限制
- 按「标准流程」步骤 1-2 完成单样本验证
- 遇到问题查「错误码体系」

### 7.3 进阶路径（熟练用户）

- 自定义字段映射：支持将源表头映射为自定义字段名
- 多 sheet 遍历：指定 `sheet_pattern` 正则匹配多个工作表
- 图片预处理：支持灰度化、二值化参数调整以提升 OCR 准确率
- 输出后处理：支持对抽取结果执行自定义 Python 函数（如单位换算）

---

## 八、参数速查表

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `file_path` | str | 是 | - | 待处理的文件路径 |
| `sheet_name` | str | 否 | `"Sheet1"` | 工作表名称 |
| `fields` | list | 是 | - | 要抽取的字段名列表 |
| `input_dir` | str | 是 | - | 批量处理的输入目录 |
| `output_dir` | str | 是 | - | 批量处理的输出目录 |
| `file_pattern` | str | 否 | `"*.xlsx"` | 文件匹配模式 |
| `ocr_confidence` | float | 否 | `0.6` | OCR 置信度阈值，低于此值输出占位符 |
| `date_format` | str | 否 | `"%Y-%m-%d"` | 日期输出格式 |
| `backup` | bool | 否 | `True` | 是否自动备份原始文件 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于数据准确性、合规性、业务决策等后果。
2. **禁止反向工程**：不得对本 Skill 的代码、逻辑、文档进行反向工程、反编译、破解或试图提取源代码。
3. **数据安全**：使用者应确保输入数据不包含违反法律法规的内容，并对敏感数据自行脱敏处理。
4. **无担保**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

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

---

*文档版本：1.0.0 | 最后更新：2024-01-01*

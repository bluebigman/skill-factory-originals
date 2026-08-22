---
slug: automatewithpython
name: automatewithpython
displayName: 办公自动化 批量脚本生成
description: 将重复性文件与表格操作转化为可执行 Python 脚本，提升工作效率。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 脚本工坊
agent_created: true
trigger_words: ["automatewithpython", "python自动化", "批量处理", "脚本生成", "办公自动化", "文件批处理", "表格清洗"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# SKILL.md — automatewithpython

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| CSV 数据清洗 | 去重、空值填充、格式统一 | `deduplicate`、`fillna` |
| 批量文件重命名 | 按规则批量修改文件名 | 添加前缀、替换关键字 |
| 表格合并拆分 | 多文件横向/纵向合并，按条件拆分 | `merge`、`split` |
| 格式转换 | CSV ↔ Excel ↔ JSON | `convert` |
| 简单报表生成 | 汇总统计并输出 Markdown/CSV | `summarize` |

### 1.2 不能做什么

- 不处理二进制文件（图片、视频、压缩包）的内容解析
- 不提供 GUI 界面，所有操作通过命令行完成
- 不连接外部 API 或数据库（纯本地文件操作）
- 不生成复杂业务逻辑（如财务核算、库存管理）的完整系统

### 1.3 适用对象

- 日常需要处理大量表格数据的办公人员
- 需要批量整理文件的个人用户
- 希望将重复操作脚本化的初级开发者

---

## 二、触发方式

### 2.1 触发词

当用户输入以下任一关键词时，本 Skill 被激活：

- `automatewithpython`
- `python自动化`
- `批量处理`
- `脚本生成`
- `办公自动化`
- `文件批处理`
- `表格清洗`

### 2.2 场景映射表

| 用户说（大白话） | 本 Skill 响应动作 |
|------------------|-------------------|
| "我有 100 个 CSV 要合并" | 生成合并脚本，输出合并后的单一文件 |
| "这个表格里重复行太多" | 生成去重脚本，保留首次出现的记录 |
| "文件名太乱了，想统一加前缀" | 生成批量重命名脚本 |
| "想把 Excel 转成 CSV" | 生成格式转换脚本 |
| "帮我统计每个月的销售额" | 生成分组汇总脚本 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| Python 环境 | 3.8 及以上 | `python --version` |
| 依赖库 | pandas、openpyxl | `pip list \| grep pandas` |
| 输入文件 | 路径无空格或已正确转义 | 直接查看路径 |
| 磁盘空间 | 至少为输入文件总大小的 2 倍 | `df -h` |

### 3.2 执行步骤

1. **准备输入文件**：将待处理的 CSV/Excel 文件放入同一目录，记录完整路径。
2. **调用命令**：在终端执行 `automatewithpython <操作类型> <输入文件>`。
3. **查看生成脚本**：命令执行后，当前目录生成 `script.py`。
4. **运行脚本**：执行 `python script.py --input <输入文件> --output <输出文件>`。
5. **检查输出**：打开输出文件，确认数据符合预期。

### 3.3 输出规范

| 输出项 | 格式 | 说明 |
|--------|------|------|
| 脚本文件 | `script.py` | 可直接运行的 Python 脚本 |
| 日志信息 | 终端输出 | 包含处理行数、耗时、异常提示 |
| 结果文件 | 由 `--output` 指定 | 默认与输入同目录，文件名加 `_processed` 后缀 |

---

## 四、置信度门控

当输入信息不足以生成可靠脚本时，本 Skill 会输出 `[需核实:字段]` 占位符，而非编造默认值。

| 场景 | 占位符示例 | 用户需补充的信息 |
|------|------------|------------------|
| 去重时未指定依据列 | `[需核实:去重依据列名]` | 指定列名，如 `--key id` |
| 合并时未指定合并键 | `[需核实:合并键]` | 指定键名，如 `--on user_id` |
| 重命名规则不明确 | `[需核实:重命名模式]` | 提供具体规则，如 `--pattern "prefix_{old}"` |
| 日期格式不明确 | `[需核实:日期格式]` | 指定格式，如 `--date-format %Y-%m-%d` |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 输入文件不存在 | `错误：找不到文件 <路径>` | 检查路径是否正确，使用绝对路径 |
| E002 | 文件格式不支持 | `错误：仅支持 .csv/.xlsx/.json` | 转换文件格式后重试 |
| E003 | 缺少必要参数 | `错误：缺少 --output 参数` | 参考 `--help` 补齐参数 |
| E004 | 依赖库缺失 | `错误：未安装 pandas` | 执行 `pip install pandas openpyxl` |
| E005 | 数据格式异常 | `错误：第 N 行数据无法解析` | 检查源文件该行内容，修复后重试 |
| E006 | 权限不足 | `错误：无法写入输出目录` | 更换目录或调整权限 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式（错误做法） | 正模式（正确做法） |
|----|-------------------|-------------------|
| 路径含空格 | 直接粘贴路径导致报错 | 用引号包裹路径：`"C:\My Files\data.csv"` |
| 编码问题 | 忽略编码直接读取 | 指定 `--encoding utf-8-sig` 处理 BOM |
| 覆盖原文件 | 输出路径与原文件相同 | 使用 `_processed` 后缀或指定新目录 |
| 忽略异常行 | 脚本中断不处理 | 使用 `--skip-errors` 跳过异常行并记录日志 |
| 内存不足 | 一次性读取大文件 | 使用 `--chunk-size 10000` 分块处理 |

### 6.2 反模式对照

- **反模式**：用户要求"处理所有文件"，但未说明处理规则。
  **正模式**：先询问具体规则，或使用 `[需核实:处理规则]` 占位符。
- **反模式**：用户提供敏感数据要求上传。
  **正模式**：明确告知本 Skill 仅本地处理，不涉及任何上传行为。

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

```bash
# 1. 去重
automatewithpython deduplicate test.csv
python script.py --input test.csv --output result.csv

# 2. 合并
automatewithpython merge *.csv
python script.py --input dir/ --output merged.csv

# 3. 转换
automatewithpython convert data.xlsx
python script.py --input data.xlsx --output data.csv
```

### 7.2 分层次阅读路径

| 读者类型 | 建议阅读章节 | 目标 |
|----------|--------------|------|
| 新手 | 一、三、七（速查卡） | 能完成基本操作 |
| 进阶 | 四、五、六 | 能处理异常和复杂场景 |
| 开发者 | 全部章节 | 能自定义扩展脚本 |

---

## 八、参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | 字符串 | 无 | 输入文件路径或目录 |
| `--output` | 字符串 | 自动生成 | 输出文件路径 |
| `--key` | 字符串 | 无 | 去重/合并依据列 |
| `--encoding` | 字符串 | `utf-8` | 文件编码 |
| `--skip-errors` | 布尔 | `False` | 跳过异常行 |
| `--chunk-size` | 整数 | 无 | 分块处理行数 |
| `--pattern` | 字符串 | 无 | 重命名规则模板 |
| `--date-format` | 字符串 | `%Y-%m-%d` | 日期解析格式 |

---

## 用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应自行承担因使用本 Skill 产生的全部责任。包括但不限于因脚本运行导致的数据丢失、系统故障、业务中断等后果。
2. **数据安全**：使用者应确保输入数据的合法性和安全性。本 Skill 不存储用户数据，所有处理均在本地完成。请勿输入包含敏感个人信息或商业机密的数据。
3. **禁止反向工程**：使用者不得对本 Skill 生成的脚本进行反向工程、反编译或试图提取源代码（除明确授权的修改外）。
4. **合规使用**：使用者应遵守所在国家/地区的法律法规，不得使用本 Skill 从事任何违法活动，包括但不限于数据窃取、侵犯他人隐私、制作恶意软件等。
5. **修改与分发**：允许使用者基于本 Skill 进行修改和再分发，但需保留原始版权声明和本协议。

---

## 许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 脚本工坊

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

---
slug: excel-data-cleaning
name: 表格清洗工坊
displayName: 表格整理 数据规范化 清洗校验
description: 将杂乱表格按规则整理为规范、可分析的结构化数据。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据工坊编辑部
agent_created: true
trigger_words: ["Excel数据清洗", "表格整理", "数据规范化", "去除重复项", "格式统一", "数据清洗", "表格去重", "格式整理"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 表格清洗工坊 Skill 文档

## 一、能力边界速查卡

本 Skill 面向**日常办公表格**（Excel/CSV/TSV）的清洗与规范化，适用于以下场景：

| 维度 | 说明 |
|------|------|
| 输入格式 | `.xlsx`、`.xls`、`.csv`（UTF-8/GBK）、`.tsv` |
| 处理对象 | 单表或多表批量处理，表头在首行 |
| 核心能力 | 字段提取、格式统一、去重、空值标记、异常值识别 |
| 输出形式 | 清洗后新文件 + 清洗日志（含失败明细） |

**能做：**

- 批量处理同一目录下命名规范一致的文件（如 `销售数据_2024Q1.xlsx`）
- 按规则提取字段（如从“姓名+身份证号”中拆分出生日期）
- 统一日期格式（如 `2024/1/5` → `2024-01-05`）
- 去除完全重复行（所有字段值一致）
- 标记缺失值、异常值（如年龄为负数、金额为文本）
- 输出清洗报告，记录每行处理结果

**不能做：**

- 无法理解语义（如无法判断“张三”和“张 三”是否同一人，除非配置规则）
- 无法处理图片、PDF 中的表格
- 无法自动识别表头不在首行的文件（需手动指定）
- 无法处理加密或损坏的文件
- 不提供数据可视化或分析功能

**适用对象：** 需要定期整理报表的运营人员、数据分析师、财务人员、行政人员。

---

## 二、触发方式与场景映射

当你的需求匹配以下任一场景时，可使用本 Skill：

| 大白话描述 | 触发词 | 实际动作 |
|------------|--------|----------|
| “帮我把这个表里的日期都改成同一种格式” | 格式统一 | 执行日期/数字格式标准化 |
| “这个表里好多重复行，帮我删掉” | 去除重复项 | 按全字段匹配去重 |
| “把姓名和手机号拆成两列” | 字段提取 | 按分隔符/正则拆分列 |
| “这表里有些格子是空的，帮我标出来” | 数据规范化 | 空值填充或标记为 `[缺失]` |
| “把几个月的表合并成一张总表” | 表格整理 | 按表头合并多文件 |

**触发词完整列表：** `Excel数据清洗`、`表格整理`、`数据规范化`、`去除重复项`、`格式统一`、`数据清洗`、`表格去重`、`格式整理`

---

## 三、标准操作流程

### 前置条件

1. 所有待处理文件放在**同一目录**下，文件名遵循统一模式（如 `数据_月份.xlsx`）
2. 每个文件的首行为表头，且表头名称一致（如均为 `姓名, 日期, 金额`）
3. 确认原始文件已备份（复制到 `backup/` 子目录）
4. 准备一个 `清洗规则.json` 配置文件（格式见下文）

### 执行步骤

**第 1 步：配置规则**

创建 `清洗规则.json`，示例：

```json
{
  "date_fields": ["日期", "下单时间"],
  "date_format": "%Y-%m-%d",
  "numeric_fields": ["金额", "数量"],
  "deduplicate": true,
  "empty_marker": "[缺失]",
  "split_rules": [
    {"field": "姓名", "separator": " ", "new_fields": ["姓", "名"]}
  ]
}
```

**第 2 步：试运行**

- 选取目录中**一个样本文件**执行清洗
- 命令：`python clean_table.py --config 清洗规则.json --input 样本文件.xlsx --output 样本_清洗后.xlsx`
- 核对输出文件：字段是否拆分正确、日期格式是否统一、空值是否标记

**第 3 步：批量执行**

- 确认样本无误后，对全量文件执行：
  `python clean_table.py --config 清洗规则.json --input-dir ./data/ --output-dir ./cleaned/`
- 每个文件生成对应的 `清洗日志.csv`，记录每行的处理状态（成功/失败/跳过）

**第 4 步：校验结果**

- 随机抽取 5-10 条输出记录，与源文件逐字段比对
- 检查日志中失败行数是否在可接受范围（建议 < 2%）
- 确认无数据丢失（总行数 = 成功行 + 失败行 + 去重移除行）

### 输出规范

| 输出项 | 格式 | 说明 |
|--------|------|------|
| 清洗后数据 | `.xlsx` 或 `.csv` | 与输入同名，加 `_cleaned` 后缀 |
| 清洗日志 | `清洗日志.csv` | 列：`文件名, 行号, 状态, 说明` |
| 去重报告 | `去重报告.txt` | 列出移除的重复行数及原因 |

---

## 四、置信度门控

当遇到以下情况时，**不猜测、不编造**，输出占位符 `[需核实:字段名]`：

- 日期格式无法解析（如 `2024年13月`）
- 数值字段包含非数字字符（如 `1,234元`）
- 拆分规则无法匹配（如姓名无空格分隔）
- 表头名称与规则配置不一致

**示例：**

| 原始值 | 处理结果 |
|--------|----------|
| `2024/02/30` | `[需核实:日期]` |
| `金额: 1,200元` | `[需核实:金额]` |
| `张三丰`（无空格） | `[需核实:姓名拆分]` |

同时，在清洗日志中标记该行为 `需人工确认`。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件无法读取 | “文件可能已损坏或格式不受支持” | 检查文件扩展名，尝试另存为 `.xlsx` |
| `E002` | 表头缺失或为空 | “首行未检测到表头” | 手动添加表头行，或配置 `header_row: 2` |
| `E003` | 日期格式无法解析 | “日期字段存在无法识别的格式” | 在规则中增加 `custom_date_formats` 列表 |
| `E004` | 数值字段含文本 | “数值字段包含非数字字符” | 配置 `numeric_clean: true` 自动去除货币符号 |
| `E005` | 拆分规则未命中 | “拆分字段未找到分隔符” | 检查分隔符配置，或改用正则表达式 |
| `E006` | 输出目录无写入权限 | “无法写入输出目录” | 检查目录权限，或更换输出路径 |

---

## 六、常见坑与反模式对照

| 常见坑（反模式） | 正确做法 |
|------------------|----------|
| **直接对原文件操作**，清洗出错后无法恢复 | 始终复制到 `backup/` 后再处理 |
| **忽略试运行**，直接批量执行导致大量错误 | 先跑单个样本，确认规则无误再全量 |
| **日期格式只写一种**，遇到 `2024/1/5` 和 `2024-01-05` 混用就报错 | 配置 `custom_date_formats` 覆盖常见变体 |
| **去重时只看部分字段**，导致误删有效数据 | 默认全字段匹配去重，如需部分字段需显式配置 |
| **清洗后不校验**，直接使用结果 | 至少抽查 5 条记录，核对关键字段 |
| **规则文件写死路径**，换目录后报错 | 使用相对路径，或通过命令行参数传入 |

---

## 七、渐进式阅读路径

### 新手路径（5 分钟上手）

1. 阅读「能力边界速查卡」确认本 Skill 能解决你的问题
2. 按「标准操作流程」第 1-2 步，配置最小规则并试运行
3. 查看输出文件与日志，确认结果符合预期
4. 如有问题，对照「错误码体系」排查

### 进阶路径（深入使用）

1. 学习 `清洗规则.json` 的全部配置项（见附录 A）
2. 使用 `split_rules` 实现复杂字段拆分（如地址拆分为省/市/区）
3. 结合 `custom_date_formats` 处理多语言日期格式
4. 批量处理时，利用日志文件自动筛选失败行进行二次处理
5. 将清洗规则模板化，供团队复用

### 附录 A：清洗规则配置项参考

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `date_fields` | array | `[]` | 需要格式化的日期字段名列表 |
| `date_format` | string | `%Y-%m-%d` | 输出日期格式（Python strftime 语法） |
| `custom_date_formats` | array | `[]` | 输入日期可能出现的格式列表 |
| `numeric_fields` | array | `[]` | 需要转为数值的字段名列表 |
| `numeric_clean` | bool | `false` | 是否自动去除货币符号、千分位逗号 |
| `deduplicate` | bool | `false` | 是否去除完全重复行 |
| `empty_marker` | string | `[缺失]` | 空值填充标记 |
| `split_rules` | array | `[]` | 字段拆分规则（见示例） |
| `header_row` | int | `1` | 表头所在行号 |

---

## 用户协议

**使用本 Skill 即表示您同意以下条款：**

1. 使用者自行承担全部责任。因使用本 Skill 产生的任何数据丢失、处理错误或业务损失，Skill 作者及发布平台不承担任何责任。
2. 禁止反向工程。不得对本 Skill 的底层实现进行反编译、反汇编或试图提取源代码（除非适用法律允许）。
3. 本 Skill 提供的输出结果仅供参考，不构成任何形式的保证或承诺。
4. 使用者应确保处理的数据符合相关法律法规，不得使用本 Skill 处理违法或侵权数据。

<!-- user-agreement-injected -->

---

## 许可证（License）

本 Skill 采用 MIT 许可证发布：

```
MIT License

Copyright (c) 2024 数据工坊编辑部

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

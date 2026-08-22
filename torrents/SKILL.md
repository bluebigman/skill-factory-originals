---
slug: torrents
name: torrents
displayName: 数据解析 结构化输出 批量转换
description: 将任意数据、文件或URL解析为结构化结果，支持批量与自定义格式。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据工坊
agent_created: true
trigger_words: ["torrents", "数据解析", "结构化输出", "批量处理", "格式转换", "SQL查询"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

# torrents — 数据解析与结构化输出 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 数据解析 | 将 CSV、JSON、TXT、日志等文本数据解析为结构化字段 | 将 `2024-01-01,张三,100` 解析为 `{date, name, amount}` |
| URL 抓取 | 从指定 URL 获取内容并解析为结构化结果 | 抓取 API 返回的 JSON 并提取关键字段 |
| SQL 查询 | 对结构化数据执行 SQL 查询（SELECT/WHERE/ORDER BY） | `SELECT name FROM data WHERE amount > 50` |
| 批量处理 | 对同一目录下的多个文件执行相同解析逻辑 | 将 `data/` 下所有 `.csv` 文件批量解析 |
| 格式转换 | 在 JSON、CSV、YAML、Markdown 表格间互相转换 | 将 JSON 数组转为 Markdown 表格 |
| 自定义格式 | 通过正则或模板定义自定义解析规则 | 提取日志中的时间戳和错误级别 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不处理二进制文件 | 仅支持文本类数据（CSV/JSON/TXT/XML/日志等） |
| 不执行远程代码 | 不会从 URL 下载并执行任何脚本 |
| 不保证数据准确性 | 解析结果依赖输入数据的规范性，异常数据需人工校验 |
| 不支持复杂嵌套 | 深度超过 5 层的嵌套 JSON 建议先预处理 |
| 不提供可视化 | 仅输出结构化文本，不生成图表或仪表盘 |

### 1.3 适用对象

- **适用**：日志分析、数据清洗、报表生成、API 响应解析、配置文件转换
- **不适用**：图像识别、音频处理、实时流数据、需要外部数据库连接的场景

---

## 二、触发方式

### 2.1 触发词

- 主触发词：`torrents`
- 同义触发词：`数据解析`、`结构化输出`、`批量处理`、`格式转换`、`SQL查询`

### 2.2 场景映射表

| 用户说（大白话） | 实际触发动作 |
|------------------|--------------|
| "帮我把这个 CSV 转成 JSON" | 调用格式转换能力，CSV → JSON |
| "解析一下这个日志文件，提取错误信息" | 调用数据解析能力，提取 error 级别条目 |
| "这个目录下所有文件都处理一遍" | 调用批量处理能力，遍历目录执行解析 |
| "从这些数据里筛选出金额大于 100 的记录" | 调用 SQL 查询能力，执行 WHERE 条件过滤 |
| "把这个 API 返回的数据整理成表格" | 调用 URL 抓取 + 格式转换能力 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 输入文件 | 文本格式（.csv/.json/.txt/.log/.xml） | 文件头检查（前 10 行） |
| 文件命名 | 同批文件命名规范一致（如 `data_01.csv`） | 目录列表核对 |
| 编码格式 | UTF-8 无 BOM（推荐） | `file` 命令或编辑器查看 |
| 目录结构 | 输入文件与输出目录分离 | 确认输出路径存在 |

### 3.2 执行步骤

#### 步骤 1：准备输入

1. 将待处理文件放入同一目录（如 `./input/`）
2. 确认文件命名规范一致（如 `data_01.csv`, `data_02.csv`）
3. 检查文件编码为 UTF-8，无 BOM 头

#### 步骤 2：试运行（单样本）

1. 选取第一个文件作为样本
2. 执行解析命令，核对输出字段名与格式
3. 检查字段类型（字符串/数字/日期）是否符合预期

**示例命令**：
```bash
# 解析单个 CSV 文件
torrents parse ./input/data_01.csv --format json

# 输出示例
{"date": "2024-01-01", "name": "张三", "amount": 100}
```

#### 步骤 3：批量执行

1. 确认试运行结果无误
2. 对全量文件执行解析
3. 保留原始文件备份（复制到 `./backup/`）

**示例命令**：
```bash
# 批量解析目录下所有 CSV 文件
torrents batch ./input/ --pattern "*.csv" --output ./output/ --format json
```

#### 步骤 4：校验结果

1. 抽查输出文件（每批至少 3 个）
2. 核对关键字段与源数据一致性
3. 检查字段完整性（无缺失、无乱码）

**校验清单**：

| 检查项 | 通过标准 |
|--------|----------|
| 字段数量 | 与源数据列数一致 |
| 字段类型 | 数字字段为数值类型，日期字段为 ISO 格式 |
| 数据完整性 | 无空值、无截断、无乱码 |
| 编码正确 | 中文显示正常，无 `?` 或 `\u` 转义 |

### 3.3 输出规范

| 输出格式 | 适用场景 | 示例 |
|----------|----------|------|
| JSON | API 对接、程序处理 | `[{"name": "张三", "amount": 100}]` |
| CSV | Excel 打开、表格处理 | `name,amount\n张三,100` |
| Markdown 表格 | 文档展示、报告 | `\| name \| amount \|` |
| YAML | 配置文件、K8s 清单 | `name: 张三\namount: 100` |

---

## 四、置信度门控

### 4.1 信息不足时的处理

当输入数据不完整或无法确认时，**不编造数据**，使用占位符标记：

| 场景 | 占位符 | 示例 |
|------|--------|------|
| 字段缺失 | `[需核实:字段名]` | `{"amount": "[需核实:amount]"}` |
| 日期格式不确定 | `[需核实:日期格式]` | `{"date": "[需核实:日期格式]"}` |
| 编码不确定 | `[需核实:编码]` | 输出前提示 `[需核实:编码]` |
| 数据来源不明 | `[需核实:来源]` | 输出前提示 `[需核实:来源]` |

### 4.2 置信度分级

| 级别 | 条件 | 处理方式 |
|------|------|----------|
| 高置信度 | 字段完整、类型明确、来源清晰 | 直接输出，无需标记 |
| 中置信度 | 字段完整但类型或格式存疑 | 输出时附加 `[需核实:字段]` 标记 |
| 低置信度 | 字段缺失或数据异常 | 输出占位符 + 提示人工检查 |

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `E001` | 文件不存在 | "未找到指定文件，请检查路径" | 1. 确认文件路径正确<br>2. 检查文件名大小写<br>3. 确认文件已放入指定目录 |
| `E002` | 编码不支持 | "文件编码非 UTF-8，无法解析" | 1. 使用 `iconv` 转换编码<br>2. 或另存为 UTF-8 无 BOM 格式 |
| `E003` | 字段缺失 | "数据缺少必要字段：`amount`" | 1. 检查源数据列名<br>2. 确认解析规则中的字段映射 |
| `E004` | 类型不匹配 | "字段 `date` 期望日期类型，实际为字符串" | 1. 检查源数据格式<br>2. 调整解析规则或预处理数据 |
| `E005` | 批量中断 | "第 3 个文件解析失败，已停止批量处理" | 1. 单独处理失败文件<br>2. 修正后重新执行批量 |
| `E006` | 输出目录不可写 | "无法写入输出目录，请检查权限" | 1. 确认目录存在<br>2. 修改目录写权限 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 文件命名混乱 | 直接批量处理命名不一致的文件 | 先统一命名规范，再执行批量 |
| 忽略试运行 | 跳过单样本测试直接全量处理 | 务必先试运行 1 个文件，核对输出 |
| 不保留备份 | 直接覆盖原始文件 | 先复制到备份目录，再执行解析 |
| 盲目信任输出 | 不校验直接使用解析结果 | 抽查至少 3 个输出文件，核对关键字段 |
| 忽略编码问题 | 直接解析非 UTF-8 文件导致乱码 | 先检查编码，必要时转换后再解析 |
| 字段映射错误 | 解析规则中字段名与源数据不一致 | 先查看源数据头部，确认列名后再定义规则 |

### 6.2 反模式示例

**反模式 1：跳过试运行**
```
❌ 错误：直接对 100 个文件执行批量解析，结果发现字段名映射错误，全部输出无效。
✅ 正确：先对 1 个文件试运行，确认字段映射正确后再批量执行。
```

**反模式 2：不保留原始数据**
```
❌ 错误：解析后直接覆盖原始 CSV 文件，后续发现解析规则有误，无法恢复。
✅ 正确：解析前将原始文件复制到 `./backup/` 目录，确保可回溯。
```

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

```
1. 准备：文件放入 ./input/，命名规范一致
2. 试运行：torrents parse ./input/sample.csv --format json
3. 批量：torrents batch ./input/ --pattern "*.csv" --output ./output/
4. 校验：抽查输出文件，核对字段与源数据一致
```

### 7.2 分层次阅读路径

#### 新手路径（5 分钟上手）

1. 阅读「能力边界」了解能做什么
2. 按「标准流程」步骤 1-2 完成单文件解析
3. 使用「错误码体系」排查常见问题

#### 进阶路径（深入使用）

1. 阅读「触发方式」了解全部能力场景
2. 学习「自定义格式」定义复杂解析规则
3. 掌握「置信度门控」处理异常数据
4. 结合「FAQ 反模式」避免常见错误

#### 专家路径（批量与自动化）

1. 设计批量处理流程，结合「前置条件」确保输入规范
2. 使用「输出规范」对接下游系统
3. 建立「校验清单」自动化检查输出质量
4. 处理「置信度门控」中的低置信度场景

---

## 八、参数参考表

### 8.1 常用参数

| 参数 | 类型 | 必填 | 说明 | 默认值 |
|------|------|------|------|--------|
| `--input` | string | 是 | 输入文件或目录路径 | 无 |
| `--output` | string | 否 | 输出目录路径 | `./output/` |
| `--format` | string | 否 | 输出格式（json/csv/yaml/md） | `json` |
| `--pattern` | string | 否 | 批量处理的文件匹配模式 | `*` |
| `--delimiter` | string | 否 | CSV 分隔符 | `,` |
| `--encoding` | string | 否 | 输入文件编码 | `utf-8` |
| `--selftest` | flag | 否 | 运行自检 | 无 |
| `--version` | flag | 否 | 显示版本信息 | 无 |

### 8.2 边界值

| 参数 | 最小值 | 最大值 | 说明 |
|------|--------|--------|------|
| 文件大小 | 1 KB | 100 MB | 超过 100 MB 建议分片处理 |
| 批量文件数 | 1 | 1000 | 超过 1000 个建议分批执行 |
| 字段数量 | 1 | 100 | 超过 100 个字段建议拆分 |
| 嵌套深度 | 1 | 5 | 超过 5 层嵌套建议预处理 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的解析结果仅供参考，不构成任何形式的保证或承诺。

2. **数据安全**：使用者应自行确保输入数据的合法性与安全性。本 Skill 不存储、不传输任何用户数据，所有处理均在本地完成。

3. **禁止反向工程**：使用者不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码。

4. **合规使用**：使用者应遵守所在国家/地区的法律法规，不得将本 Skill 用于任何非法用途。

5. **免责声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的保证。因使用本 Skill 造成的任何直接或间接损失，作者不承担任何责任。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 数据工坊

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*

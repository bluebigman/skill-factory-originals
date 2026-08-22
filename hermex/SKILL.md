---
slug: hermex
name: hermex
displayName: 信息萃取 结构化输出 数据整理
description: 从网页、文件或数据中提取关键信息，按约定格式输出结构化结果。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨
agent_created: true
trigger_words: ["爬虫采集", "数据提取", "结构化输出", "网页抓取", "信息整理", "字段抽取", "内容解析"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# hermex — 信息萃取与结构化输出 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 网页内容提取 | 从 HTML 页面中抽取正文、标题、链接、表格等 | 抓取新闻页面的标题、发布时间、正文 |
| 文件内容解析 | 从 TXT、CSV、JSON、Markdown 等文本类文件中提取字段 | 从 CSV 中提取指定列并重组 |
| 数据字段映射 | 将非结构化文本映射到预定义字段结构 | 将一段产品描述拆分为名称、价格、规格 |
| 批量处理 | 对多个文件或 URL 执行相同的提取逻辑 | 对 100 个商品页面执行统一抽取 |
| 格式校验 | 检查输出结果是否符合约定的字段类型与必填项 | 校验日期格式是否为 YYYY-MM-DD |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不处理二进制文件 | PDF、DOCX、图片等需先转换为文本格式 |
| 不执行 JavaScript 渲染 | 动态加载的网页内容需先通过其他工具获取渲染后 HTML |
| 不进行语义理解 | 只能按规则提取，无法判断"言外之意"或情感倾向 |
| 不自动修正源数据 | 源数据缺失或错误时，仅标记占位符，不猜测填充 |
| 不保证 100% 覆盖率 | 复杂嵌套结构或异常格式可能导致部分字段提取失败 |

### 1.3 适用对象

- 需要从大量网页或文本文件中提取固定字段的运营人员
- 需要将非结构化数据转为表格化数据的分析人员
- 需要定期采集特定信息并归档的调研人员

---

## 二、触发方式

### 2.1 触发词

当你的指令中包含以下任一词汇或同义表达时，本 Skill 将被激活：

- 爬虫采集 / 网页抓取 / 数据提取 / 结构化输出 / 信息整理 / 字段抽取 / 内容解析
- 将这段内容整理成表格 / 提取其中的关键信息 / 按字段输出

### 2.2 场景映射表

| 你说的话（大白话） | Skill 实际执行的动作 |
|-------------------|---------------------|
| "帮我把这个网页里的商品信息抓下来" | 解析 HTML，提取商品名称、价格、库存等字段 |
| "这个 CSV 文件里数据太乱了，帮我整理一下" | 读取 CSV，按预设字段重新映射并输出 |
| "把这篇文章里的核心观点提取出来" | 识别段落结构，抽取标题、摘要、关键词 |
| "我有 50 个文件，每个里面都有联系人信息，帮我汇总" | 批量遍历文件，统一提取姓名、电话、邮箱 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 输入文件位置 | 与 Skill 运行目录一致，或提供完整路径 | 确认文件可读 |
| 命名规范 | 文件名前缀一致（如 `data_01.txt`、`data_02.txt`） | 列出目录核对 |
| 字段定义 | 明确需要提取哪些字段及类型 | 与需求方确认 |
| 输出格式 | 约定输出为 JSON / CSV / Markdown 表格 | 提前确定 |

### 3.2 执行步骤

**第一步：准备输入**

1. 将所有待处理文件放入同一目录，确认命名规范一致。
2. 若为网页抓取，准备 URL 列表文件（每行一个 URL）。
3. 明确字段清单，例如：`title`（字符串）、`price`（数字）、`date`（日期）。

**第二步：试运行（单样本验证）**

1. 选取 1 个代表性样本（文件或 URL）。
2. 执行提取，检查输出字段是否齐全、格式是否正确。
3. 若字段缺失或格式不符，调整提取规则后重试。

**第三步：批量执行**

1. 确认试运行无误后，对全量数据执行提取。
2. 保留原始文件备份，不覆盖源文件。
3. 输出结果写入新文件（如 `output.json` 或 `output.csv`）。

**第四步：校验结果**

1. 随机抽查 5% 的输出条目。
2. 核对关键字段（如标题、日期、金额）与源数据是否一致。
3. 若发现系统性偏差，定位规则问题并修正后重新执行。

### 3.3 输出规范

| 输出格式 | 适用场景 | 示例 |
|----------|----------|------|
| JSON | 需要程序化处理 | `{"title": "示例", "price": 99.0}` |
| CSV | 需要表格化查看 | `title,price\n示例,99.0` |
| Markdown 表格 | 需要直接阅读 | `\| 标题 \| 价格 \|` |

**字段类型约定：**

| 类型 | 说明 | 示例 |
|------|------|------|
| string | 字符串 | `"2024年1月"` |
| number | 数字（浮点或整数） | `99.9` |
| date | 日期，格式 `YYYY-MM-DD` | `2024-01-15` |
| array | 数组 | `["a", "b"]` |
| object | 嵌套对象 | `{"name": "x"}` |

---

## 四、置信度门控

### 4.1 占位符规则

当源数据中某字段缺失、格式异常或无法解析时，**不得编造内容**，必须输出占位符：

```
[需核实:字段名]
```

示例：

```json
{
  "title": "某产品介绍",
  "price": "[需核实:price]",
  "date": "2024-01-15"
}
```

### 4.2 置信度分级

| 级别 | 含义 | 输出方式 |
|------|------|----------|
| 高（≥90%） | 字段值直接从源数据提取，无歧义 | 正常输出 |
| 中（70-89%） | 字段值经过格式转换或规则映射 | 正常输出，并在备注中说明转换逻辑 |
| 低（<70%） | 字段值存在多种可能或源数据冲突 | 输出占位符 `[需核实:字段名]` |

### 4.3 禁止行为

- 禁止用默认值（如 `0`、`"未知"`）填充缺失字段
- 禁止根据上下文猜测缺失内容
- 禁止将占位符替换为推测值

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 文件不存在或路径错误 | "未找到指定文件，请检查路径" | 1. 确认文件路径 2. 检查文件名拼写 |
| E002 | 文件格式不支持 | "当前文件类型不支持，请转换为 TXT/CSV/JSON/Markdown" | 1. 转换文件格式 2. 重新执行 |
| E003 | 字段定义缺失 | "未指定需要提取的字段，请提供字段清单" | 1. 列出字段名及类型 2. 重新执行 |
| E004 | 提取规则匹配失败 | "未匹配到任何内容，请检查源数据格式" | 1. 检查源数据是否为空 2. 调整提取规则 |
| E005 | 批量执行中断 | "批量处理在第 N 个文件处中断" | 1. 检查第 N 个文件格式 2. 修复后从断点继续 |
| E006 | 输出格式冲突 | "输出格式与字段类型不兼容" | 1. 检查字段类型定义 2. 调整输出格式 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 跳过试运行直接批量 | 直接对 100 个文件执行，结果全部字段错位 | 先跑 1 个样本，确认无误再批量 |
| 覆盖原始文件 | 将提取结果写回原文件，导致源数据丢失 | 输出到新文件，保留原始备份 |
| 忽略缺失字段 | 缺失字段留空或填 `N/A` | 使用 `[需核实:字段名]` 占位 |
| 不校验输出 | 批量执行后直接使用，未抽查 | 至少抽查 5% 条目核对关键字段 |
| 规则写死 | 提取规则硬编码，换一批数据就失效 | 将规则参数化，便于调整 |

### 6.2 反模式示例

**错误做法：**

```
输入：data_01.txt 到 data_50.txt
操作：直接批量提取，未试运行
结果：50 个文件全部输出，但 date 字段全部解析失败
```

**正确做法：**

```
输入：data_01.txt 到 data_50.txt
操作：先提取 data_01.txt，检查 date 字段格式
调整：修正日期解析规则
执行：批量提取全部 50 个文件
校验：抽查 3 个文件，确认 date 字段正确
```

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 放文件 → 2. 定字段 → 3. 跑样本 → 4. 查输出 → 5. 跑批量 → 6. 抽查
```

### 7.2 分层次阅读路径

**新手路径（首次使用）：**

1. 阅读「能力边界」了解适用范围
2. 阅读「标准流程」按步骤执行
3. 遇到问题查「错误码体系」

**进阶路径（熟练使用）：**

1. 阅读「置信度门控」理解占位符机制
2. 阅读「FAQ 反模式」避免常见错误
3. 自定义字段映射规则，适配复杂场景

### 7.3 字段定义模板

```json
{
  "fields": [
    {"name": "title", "type": "string", "required": true},
    {"name": "price", "type": "number", "required": false},
    {"name": "date", "type": "date", "required": true}
  ]
}
```

---

## 八、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。因使用本 Skill 导致的任何直接或间接损失，Skill 作者及发布平台不承担任何责任。
2. **合法使用**：使用者须确保使用本 Skill 的行为符合当地法律法规及目标网站的服务条款。禁止将本 Skill 用于非法数据采集、侵犯隐私或其他违规用途。
3. **禁止反向工程**：使用者不得对本 Skill 进行反向工程、反编译、破解或试图提取底层算法。
4. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

本 Skill 采用 MIT 许可证发布。

### MIT License

```
MIT License

Copyright (c) 2024 林墨

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

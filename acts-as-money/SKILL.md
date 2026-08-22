---
slug: acts-as-money
name: acts-as-money
displayName: 金额识别 货币解析 字段提取
description: 从混合文本中提取金额与币种，输出标准化JSON数据，供下游系统直接使用。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据管道工坊
agent_created: true
trigger_words: ["acts as money", "金额转换", "货币解析", "money gem", "金额字段处理", "货币识别", "金额提取", "币种解析"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# acts-as-money — 金额与币种提取工具

## 一、能力边界（一页纸速查卡）

### 能做什么

| 能力项 | 说明 |
|--------|------|
| 货币符号识别 | 支持 `$`、`€`、`£`、`¥`、`₹` 等常见符号，以及 `USD`、`EUR`、`CNY`、`JPY` 等三字母代码 |
| 数字片段提取 | 从文本中定位货币标识相邻的数字片段，支持千分位逗号/点号、小数点 |
| 数值标准化 | 将不同格式的金额统一转换为十进制数值，输出为 JSON |
| 置信度评估 | 对每次提取结果给出高/中/低三档置信度，辅助人工复核 |
| 批量处理 | 支持 CSV 文件按列批量处理，支持超大文件分块 |
| 格式提示 | 可通过参数指定欧洲数字格式（`1.234,56`）等区域格式 |

### 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不识别自然语言金额 | 如"大约三千块"、"预算充足"等非结构化表达不处理 |
| 不处理汇率换算 | 仅提取金额与币种，不做币种间转换 |
| 不判断金额合理性 | 不校验金额是否超出业务合理范围 |
| 不识别复合金额 | 如"$100-$200"范围表达，仅提取第一个数字 |
| 不处理手写体/图片 | 仅接受 UTF-8 编码的文本输入 |

### 适用对象

- 需要从合同、发票、报表、日志等文本中批量提取金额字段的开发者
- 需要将非结构化文本中的金额数据导入数据库或 BI 工具的数据工程师
- 需要做财务数据清洗、审计复核的运维或分析人员

---

## 二、触发方式

### 触发词

直接使用以下任一短语即可激活本 Skill：

- `acts as money`
- `金额转换`
- `货币解析`
- `money gem`
- `金额字段处理`
- `货币识别`
- `金额提取`
- `币种解析`

### 场景映射表

| 你说的话 | 实际需求 | 本 Skill 的动作 |
|----------|----------|-----------------|
| "帮我把这段合同里的金额都提出来" | 从合同文本中提取所有金额字段 | 扫描文本，提取货币符号+数字，输出 JSON 数组 |
| "这个 CSV 的第三列是金额，帮我处理一下" | 批量处理 CSV 文件中的金额列 | 读取文件，按列提取，输出带置信度的 JSON |
| "这个日志里混着各种格式的金额，能统一吗？" | 统一不同格式的金额表达 | 识别格式，标准化为十进制数值，标注置信度 |
| "我要把金额导入数据库，格式要干净" | 生成可直接入库的 JSON 数据 | 输出合法 JSON，字段结构固定，可直接映射 |

---

## 三、标准流程

### 前置条件

1. 输入文本必须为 UTF-8 编码
2. 如需批量处理，准备 CSV 文件（含表头）
3. 确认是否需要自定义货币符号（编辑 `currencies.json`）

### 执行步骤

#### 步骤 1：安装确认

```bash
acts as money --selftest
```

预期输出：`selftest passed` 或类似成功提示。

#### 步骤 2：单条文本测试

```bash
acts as money --input "本次采购费用为 USD 1,234.56，另加运费 $89.00"
```

预期输出：

```json
[
  {
    "currency": "USD",
    "amount": 1234.56,
    "raw_text": "USD 1,234.56",
    "confidence": "high",
    "needs_review": false
  },
  {
    "currency": "USD",
    "amount": 89.00,
    "raw_text": "$89.00",
    "confidence": "high",
    "needs_review": false
  }
]
```

#### 步骤 3：批量处理 CSV

```bash
acts as money --file invoices.csv --column amount
```

输出为 JSON 数组，每条记录包含原始行号、提取结果、置信度。

#### 步骤 4：理解置信度

| 置信度 | 含义 | 建议动作 |
|--------|------|----------|
| high | 货币标识与数字格式明确，无歧义 | 直接使用 |
| medium | 存在格式歧义（如千分位与小数点混淆） | 抽查确认 |
| low | 数字格式不明确或货币标识缺失 | 人工核对原始文本 |

#### 步骤 5：处理 low 置信度

当输出中出现 `"confidence": "low"` 时：

1. 系统自动附加 `"needs_review": true` 标记
2. 回到原始文本，人工核对 `raw_text` 字段对应的片段
3. 如需 CI/CD 拦截，使用 `--strict` 参数（low 置信度时返回非零退出码）

### 输出规范

输出始终为合法 JSON，结构如下：

```json
{
  "results": [
    {
      "currency": "CNY",
      "amount": 1234.56,
      "raw_text": "￥1,234.56",
      "confidence": "high",
      "needs_review": false
    }
  ],
  "meta": {
    "input_source": "text",
    "processed_at": "2025-01-01T12:00:00Z",
    "total_found": 1
  }
}
```

---

## 四、置信度门控

### 信息不足时的处理

当遇到以下情况时，系统不会编造数据，而是输出占位符：

| 情况 | 输出 |
|------|------|
| 货币标识缺失但数字明确 | `"currency": "unknown"`，置信度 medium |
| 数字格式无法解析 | `"amount": null`，置信度 low |
| 文本片段不完整 | `"raw_text": "[需核实:原始片段]"` |

### 占位符规范

- 所有需人工确认的字段使用 `[需核实:字段名]` 格式
- 占位符不会出现在 `amount` 或 `currency` 字段中（这两个字段要么有值，要么为 null）
- 占位符仅出现在 `raw_text` 或 `note` 字段中

### 门控策略

| 场景 | 策略 |
|------|------|
| 常规使用 | 接受所有置信度输出，人工抽查 low 置信度记录 |
| CI/CD 集成 | 使用 `--strict`，low 置信度时退出码非零 |
| 财务入账 | 建议仅接受 high 置信度，其余全部人工复核 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入为空 | "输入文本为空，请提供至少一个字符" | 检查输入参数 |
| `E002` | 编码错误 | "输入不是有效的 UTF-8 编码" | 转换文件编码后重试 |
| `E003` | 文件不存在 | "指定的文件路径不存在" | 检查路径是否正确 |
| `E004` | 列名不存在 | "CSV 中未找到指定的列名" | 检查表头，确认列名 |
| `E005` | 格式提示冲突 | "指定的格式提示与检测到的格式冲突" | 移除冲突的格式提示 |
| `E006` | 配置文件错误 | "currencies.json 格式错误" | 检查 JSON 语法，确认字段结构 |
| `E007` | 分块大小无效 | "chunk-size 必须为正整数" | 重新指定分块大小 |

---

## 六、FAQ 反模式

### 常见坑 1：忽略格式歧义

**错误做法**：直接处理欧洲格式文本，不指定格式提示。

```bash
# 错误：1.234,56 会被解析为 1.234（千分位），而非 1234.56
acts as money --input "金额为 1.234,56 欧元"
```

**正确做法**：

```bash
acts as money --input "金额为 1.234,56 欧元" --format-hint european
```

### 常见坑 2：在 CI 中忽略 low 置信度

**错误做法**：不使用 `--strict`，low 置信度数据直接入库。

**正确做法**：

```bash
acts as money --file data.csv --column amount --strict
# 当存在 low 置信度时，命令返回非零退出码，阻断流水线
```

### 常见坑 3：自定义货币未配置

**错误做法**：直接使用未在 `currencies.json` 中定义的货币符号。

**正确做法**：先编辑 `currencies.json`，添加自定义货币：

```json
{
  "BTC": {
    "symbol": "₿",
    "name": "Bitcoin",
    "decimals": 8
  }
}
```

### 常见坑 4：超大文件一次性处理

**错误做法**：直接处理 100MB+ 文件，导致内存溢出。

**正确做法**：

```bash
acts as money --file huge.csv --column amount --chunk-size 10000
```

### 常见坑 5：忽略 `needs_review` 标记

**错误做法**：直接消费所有输出，不检查 `needs_review` 字段。

**正确做法**：在数据管道中过滤 `needs_review: true` 的记录，转入人工审核队列。

---

## 七、渐进式披露

### 速查卡（30 秒上手）

```bash
# 单条文本
acts as money --input "费用 $1,200.50"

# CSV 批量
acts as money --file data.csv --column amount

# 严格模式（CI 用）
acts as money --file data.csv --column amount --strict

# 欧洲格式
acts as money --input "1.234,56 €" --format-hint european
```

### 新手路径（首次使用）

1. 运行 `acts as money --selftest` 确认安装
2. 用 `--input` 测试 3-5 条简单文本，观察输出格式
3. 准备一个小 CSV（10 行以内），用 `--file` + `--column` 处理
4. 查看输出中的 `confidence` 字段，理解不同置信度的含义
5. 对 low 置信度的记录，回到原始文本人工核对

### 进阶路径（深度使用）

1. **格式歧义处理**：学习欧洲数字格式（`1.234,56` = 1234.56），使用 `--format-hint` 参数
2. **CI/CD 集成**：使用 `--strict` 模式，让 low 置信度导致非零退出码，阻断发布流程
3. **自定义货币扩展**：编辑配置文件 `currencies.json`，添加自定义货币符号
4. **性能优化**：对超大文件（>100MB），使用 `--chunk-size` 参数分块处理
5. **下游对接**：将输出 JSON 直接导入数据库（如 PostgreSQL 的 JSONB 字段）或报表工具（如 Tableau）

---

## 八、参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | string | 无 | 单条文本输入 |
| `--file` | string | 无 | CSV 文件路径 |
| `--column` | string | 无 | CSV 中要处理的列名 |
| `--format-hint` | string | `auto` | 数字格式提示：`auto`/`european`/`us` |
| `--strict` | bool | `false` | low 置信度时返回非零退出码 |
| `--chunk-size` | int | `5000` | 分块处理的行数 |
| `--selftest` | bool | `false` | 运行自检 |
| `--version` | bool | `false` | 显示版本号 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应自行承担因使用本 Skill 产生的全部责任。本 Skill 仅提供文本处理功能，不构成任何财务、法律或投资建议。

2. **数据安全**：使用者应对输入数据的合法性、合规性负责。本 Skill 不存储、不传输任何用户数据至第三方。所有处理均在本地完成。

3. **合规使用**：使用者应确保使用本 Skill 的行为符合当地法律法规及平台规定。因违规使用产生的后果由使用者自行承担。

4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性的担保。

5. **禁止反向工程**：使用者不得对本 Skill 进行反向工程、反编译、反汇编或试图提取源代码。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2025 数据管道工坊

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

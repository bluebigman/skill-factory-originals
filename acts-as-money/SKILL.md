---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: acts-as-money
name: acts-as-money
displayName: 金额解析 货币识别 字段清洗
description: 将混合文本中的金额与币种解析为标准化结构化数据，供下游系统直接使用。
version: 1.0.2
rules_version: cpr-20260811-n351
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/acts-as-money
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingDataWorks
agent_created: true
trigger_words: ["acts as money", "金额转换", "货币解析", "money gem", "金额字段处理", "金额清洗", "币种提取"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# acts-as-money — 金额解析与货币字段标准化

## 一、能力边界（一页纸速查卡）

### 1.1 本技能能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 混合文本金额提取 | 从一段文字中识别并抽取金额数值 | `"订单总价 1,234.56 美元"` → `1234.56` |
| 多格式数值解析 | 支持千分位逗号、小数点、正负号、括号负数 | `(1,234.56)` → `-1234.56` |
| 货币符号识别 | 识别常见符号（$、€、¥、£ 等） | `$100` → `USD`（需结合上下文） |
| ISO 4217 代码识别 | 识别三字母货币代码 | `JPY 5000` → `JPY` |
| 批量文件处理 | 从 CSV / JSON 文件中提取金额字段 | 读取 `orders.csv` 中所有金额列 |
| 公开 URL 抓取 | 从无需认证的公开网页中提取金额 | 抓取公开报价页面 |
| 置信度标注 | 每条解析结果附带高/中/低置信度及原因 | 见 §四 |

### 1.2 本技能不做什么

| 边界项 | 说明 |
|--------|------|
| 不做汇率换算 | 保留原始币种与数值，不进行任何汇率转换 |
| 不访问私有资源 | 需要登录、API Key 或认证的 URL 一律拒绝 |
| 不处理图片/扫描件 | OCR 超出本技能范围 |
| 不推断缺失币种 | 输入未标注币种时，输出 `currency: null` 并降置信度 |
| 不做金额运算 | 不进行加减乘除、汇总、比较等操作 |

### 1.3 适用对象

- 需要从自由文本、报表、日志中抽取金额字段的数据工程师
- 需要批量清洗历史数据中金额格式的运维人员
- 需要将非标准金额格式转为标准结构的业务系统集成方

---

## 二、触发方式

### 2.1 触发词

以下任一方式均可激活本技能：

- 直接调用：`acts as money`
- 中文指令：`金额转换`、`货币解析`、`金额清洗`、`币种提取`
- 场景描述：`把这段文本里的钱都提出来`、`帮我标准化这些金额字段`

### 2.2 场景映射表

| 用户说（大白话） | 技能实际执行 |
|------------------|--------------|
| "这个 CSV 里的金额列格式太乱了，帮我统一一下" | 读取 CSV，识别金额列，逐行解析并输出标准结构 |
| "这段合同里提到的赔偿金额是多少？" | 从文本中抽取所有金额及币种，标注置信度 |
| "这个网页上的价格能抓下来吗？" | 抓取公开 URL 内容，提取金额字段 |
| "¥1,234 和 USD 500 能统一格式吗？" | 解析两种格式，输出统一 JSON 结构 |

---

## 三、标准处理流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| 输入格式 | 纯文本字符串、CSV 文件路径、JSON 文件路径、公开 URL |
| 文件编码 | UTF-8（其他编码自动尝试检测，失败则报错） |
| 网络 | 仅抓取公开 URL，需可访问外网 |
| 依赖 | Python 3.8+，无需额外安装第三方库（标准库实现） |

### 3.2 执行步骤

#### 步骤 1：输入接收

接受以下任一输入形式：

- 命令行参数：`--input "文本内容"` 或 `--file path/to/file.csv`
- 交互式输入：直接粘贴文本后回车
- 管道输入：`echo "价格 $99.99" | acts-as-money`

#### 步骤 2：文本预处理

1. 去除不可见字符（零宽空格、BOM 头等）
2. 统一换行符为 `\n`
3. 若为文件，按行拆分并保留行号

#### 步骤 3：金额模式匹配

按以下优先级依次匹配：

| 优先级 | 模式 | 示例 |
|--------|------|------|
| 1 | 货币符号 + 数值 | `$1,234.56`、`€99` |
| 2 | ISO 代码 + 数值 | `USD 500`、`JPY 10000` |
| 3 | 数值 + 货币符号 | `500 USD`、`99€` |
| 4 | 纯数值（无币种） | `1,234.56` → `currency: null` |

数值格式支持：

- 千分位：`1,234,567.89`
- 小数点：`1234.56` 或 `1234,56`（欧洲格式，自动识别）
- 负数：`-500` 或 `(500)`（括号表示法）
- 科学计数法：`1.5e3`（不推荐，但可解析）

#### 步骤 4：币种识别

| 输入形式 | 识别逻辑 | 输出 |
|----------|----------|------|
| `$` | 默认 USD（若上下文出现其他币种则按上下文） | `USD` |
| `€` | 默认 EUR | `EUR` |
| `¥` | 默认 CNY（若上下文出现 JPY 则按 JPY） | `CNY` 或 `JPY` |
| `£` | 默认 GBP | `GBP` |
| 三字母代码 | 直接映射 ISO 4217 | 对应代码 |
| 无标识 | 不推断 | `null` |

#### 步骤 5：置信度评估

| 置信度 | 判定条件 |
|--------|----------|
| 高 | 币种明确 + 数值格式标准（无歧义） |
| 中 | 币种明确但数值格式有歧义（如 `1,234` 可能是 1.234 或 1234） |
| 低 | 币种缺失、数值格式异常、上下文冲突 |

低置信度时，输出中附加 `reason` 字段说明原因。

#### 步骤 6：输出结构化结果

```json
{
  "results": [
    {
      "original": "$1,234.56",
      "amount": 1234.56,
      "currency": "USD",
      "confidence": "high",
      "reason": null,
      "position": {"start": 0, "end": 9}
    }
  ],
  "meta": {
    "input_type": "text",
    "total_found": 1,
    "processing_time_ms": 12
  }
}
```

### 3.3 输出规范

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `original` | string | 是 | 原始匹配文本 |
| `amount` | number | 是 | 解析后的数值（浮点数） |
| `currency` | string/null | 是 | ISO 4217 代码或 null |
| `confidence` | string | 是 | `high` / `medium` / `low` |
| `reason` | string/null | 否 | 低置信度时的原因说明 |
| `position` | object | 否 | 在原文本中的起止位置（文本输入时提供） |

---

## 四、置信度门控

### 4.1 信息不足时的处理

当出现以下情况时，**不编造数据**，输出占位符 `[需核实:字段名]`：

| 场景 | 输出示例 |
|------|----------|
| 币种缺失 | `"currency": null, "confidence": "low", "reason": "missing_currency"` |
| 数值格式歧义 | `"amount": [需核实:千分位或小数点], "confidence": "low"` |
| 上下文冲突 | `"currency": [需核实:上下文冲突], "confidence": "low"` |

### 4.2 置信度降级规则

| 触发条件 | 降级至 |
|----------|--------|
| 币种缺失 | 低 |
| 数值含千分位且小数位为 0 | 中 |
| 括号负数表示法 | 中（需确认是否为负数） |
| 货币符号与 ISO 代码同时出现且不一致 | 低 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入为空 | "未检测到任何输入内容，请提供文本、文件路径或 URL。" | 检查输入参数是否为空 |
| `E002` | 文件不存在 | "指定的文件路径不存在，请确认路径是否正确。" | 核对文件路径 |
| `E003` | 文件编码不支持 | "文件编码无法识别，请转换为 UTF-8 后重试。" | 用文本编辑器转换编码 |
| `E004` | URL 无法访问 | "目标 URL 无法访问，可能原因：网络不通、需要认证、已被屏蔽。" | 检查网络或更换 URL |
| `E005` | 未匹配到任何金额 | "在输入内容中未找到符合格式的金额数据。" | 检查输入文本是否包含金额 |
| `E006` | 输入格式不支持 | "不支持的输入类型，仅支持文本、CSV、JSON、公开 URL。" | 转换输入格式 |

---

## 六、FAQ 反模式对照

### 6.1 常见坑

| 坑 | 反模式（错误做法） | 正模式（正确做法） |
|----|-------------------|-------------------|
| 千分位误判 | 将 `1,234` 直接解析为 `1.234` | 根据上下文判断：若后跟 `.00` 则为千分位 |
| 币种默认 | 输入 `¥100` 直接输出 `JPY` | 检查上下文：若出现 `人民币` 字样则输出 `CNY` |
| 括号负数 | 将 `(500)` 解析为 `500` | 识别括号为负数标记，输出 `-500` |
| 多币种混排 | 统一使用第一个出现的币种 | 每个金额独立识别币种 |
| 忽略置信度 | 低置信度结果直接使用 | 低置信度结果必须标注并人工复核 |

### 6.2 反模式示例

**错误做法：**
```
输入: "价格 ¥1,000 和 $200"
输出: [{"amount": 1000, "currency": "CNY"}, {"amount": 200, "currency": "CNY"}]
```

**正确做法：**
```
输入: "价格 ¥1,000 和 $200"
输出: [
  {"amount": 1000, "currency": "CNY", "confidence": "high"},
  {"amount": 200, "currency": "USD", "confidence": "high"}
]
```

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
输入 → 解析 → 输出

示例：
  输入: "订单金额 $1,234.56，运费 50 USD"
  输出: [
    {"amount": 1234.56, "currency": "USD", "confidence": "high"},
    {"amount": 50, "currency": "USD", "confidence": "high"}
  ]
```

### 7.2 新手路径（首次使用）

1. 准备一段包含金额的文本
2. 调用 `acts as money --input "你的文本"`
3. 查看输出的 JSON 结果
4. 若置信度为 `low`，人工核对原始文本

### 7.3 进阶路径（批量处理）

1. 准备 CSV 文件，确认金额列
2. 调用 `acts as money --file data.csv --column amount`
3. 检查输出中的 `confidence` 字段
4. 对低置信度行进行人工复核
5. 将结果写回新文件

### 7.4 参数速查

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | string | 无 | 直接输入文本 |
| `--file` | string | 无 | 输入文件路径（CSV/JSON） |
| `--url` | string | 无 | 公开 URL |
| `--column` | string | 无 | 指定 CSV 中要解析的列名 |
| `--output` | string | stdout | 输出文件路径 |
| `--format` | string | json | 输出格式（json/csv） |
| `--selftest` | flag | 无 | 运行自检 |
| `--version` | flag | 无 | 显示版本号 |

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。本 Skill 提供的解析结果仅供参考，不构成任何形式的专业建议或保证。因使用本 Skill 导致的任何直接或间接损失，作者不承担任何责任。

2. **禁止反向工程**：禁止对本 Skill 进行反向工程、反编译、破解、篡改或试图提取源代码（除非适用法律允许）。

3. **合规使用**：使用者应确保使用本 Skill 的行为符合当地法律法规及平台规定。

4. **数据安全**：使用者应对输入数据的合法性、合规性负责。本 Skill 不存储、不传输任何用户数据至第三方。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

```
MIT License

Copyright (c) 2026 LingDataWorks

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*

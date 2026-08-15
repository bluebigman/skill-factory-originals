---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: acts-as-money
name: acts-as-money
displayName: 财务文本 金额解析 货币标准化
description: 从混合文本中提取金额与币种，输出标准化JSON数据，供下游系统直接使用。
version: 1.0.4
rules_version: cpr-20260815-n476
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/acts-as-money
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Studio
agent_created: true
trigger_words: ["acts as money", "金额转换", "货币解析", "money gem", "金额字段处理", "货币识别", "金额提取", "币种标准化"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# acts-as-money — 金额与币种标准化提取器

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 单条文本解析 | 从一段文字中提取所有金额及其币种 | `"订单总额 USD 1,200.50，运费 EUR 45"` → 两条记录 |
| 批量文件处理 | 读取 CSV/TSV 文件，对指定列逐行提取 | `--file data.csv --column amount` |
| 多币种识别 | 支持常见货币符号与代码（USD/EUR/CNY/JPY/GBP 等 30+ 种） | `$`、`€`、`¥`、`£`、`USD`、`EUR`、`人民币` |
| 数字格式兼容 | 处理千分位逗号、小数点、欧洲反写格式 | `1,234.56` 与 `1.234,56` 均识别为 1234.56 |
| 置信度评估 | 每条输出附带 `confidence` 字段（high/medium/low） | 格式歧义时标记为 `low` |
| 标准化输出 | 统一输出为 `{ "amount": 1234.56, "currency": "EUR", "confidence": "high" }` | 下游直接入库 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行汇率换算 | 只提取与标准化，不做币种间转换 |
| 不识别手写体/图片 | 仅处理文本输入，不接 OCR |
| 不处理非金额数字 | 电话号码、日期、邮编等不会被提取 |
| 不推断隐含币种 | 若文本未标注币种，输出 `currency: null` 并降置信度 |
| 不修改源文件 | 默认只输出到 stdout 或指定输出文件 |

### 1.3 适用对象

- 财务系统对接人员：需要将合同、发票、报表中的金额批量结构化
- 数据分析师：清洗混合格式的金额字段
- 后端开发者：需要标准化金额 API 的调用方
- 审计人员：需要快速核对多币种金额的准确性

---

## 二、触发方式

### 2.1 触发词

当输入包含以下任一关键词时，本 Skill 自动激活：

- `acts as money`
- `金额转换`
- `货币解析`
- `money gem`
- `金额字段处理`
- `货币识别`
- `金额提取`
- `币种标准化`

### 2.2 场景映射表

| 用户说（大白话） | 实际触发动作 |
|------------------|--------------|
| "帮我把这段文字里的钱都找出来" | 调用单条文本解析 |
| "这个 CSV 里的金额列格式很乱，帮我统一" | 调用批量文件处理 |
| "看看这合同里有没有美元和欧元的金额" | 调用多币种提取 |
| "这个数字 1.234,56 到底是多少钱？" | 调用格式歧义解析，输出 low 置信度 |
| "把提取结果存到新文件里" | 调用 `--output` 参数写文件 |

---

## 三、标准流程

### 3.1 前置条件

- 输入文本为 UTF-8 编码
- 文件处理时，文件需为 CSV/TSV 格式，且包含表头
- 系统已安装 Python 3.8+（若使用 CLI 方式）

### 3.2 执行步骤

#### 步骤 1：准备输入

**方式 A：单条文本**

```bash
acts as money --input "采购合同总价 USD 15,000.00，含税。另付运费 EUR 250.50。"
```

**方式 B：文件批量**

```bash
acts as money --file invoices.csv --column amount --output result.json
```

参数说明：

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | 二选一 | 无 | 待解析的文本字符串 |
| `--file` | 二选一 | 无 | 待解析的 CSV/TSV 文件路径 |
| `--column` | 与 `--file` 搭配 | 无 | 指定要解析的列名 |
| `--output` | 否 | stdout | 输出 JSON 文件路径 |
| `--selftest` | 否 | 无 | 运行内置自检 |
| `--version` | 否 | 无 | 显示版本号 |

#### 步骤 2：执行解析

系统按以下顺序处理：

1. 扫描文本中的货币符号/代码（正则匹配）
2. 对每个货币标识，提取其相邻的数字片段
3. 根据数字格式规则（千分位、小数点位置）解析数值
4. 计算置信度：
   - `high`：格式明确，无歧义（如 `USD 1,200.50`）
   - `medium`：格式可识别但存在轻微歧义（如 `¥1000` 无小数位）
   - `low`：格式存在多解（如 `1.234,56` 可能是欧洲格式也可能是美国格式）

#### 步骤 3：查看输出

```json
{
  "results": [
    {
      "original_text": "USD 15,000.00",
      "amount": 15000.00,
      "currency": "USD",
      "confidence": "high",
      "position": [0, 14]
    },
    {
      "original_text": "EUR 250.50",
      "amount": 250.50,
      "currency": "EUR",
      "confidence": "high",
      "position": [24, 34]
    }
  ],
  "summary": {
    "total_found": 2,
    "low_confidence_count": 0,
    "processing_time_ms": 12
  }
}
```

#### 步骤 4：低置信度处理

当某条结果 `confidence` 为 `low` 时：

1. 系统在输出中附加 `"needs_review": true` 标记
2. 建议人工核对原始文本片段
3. 可通过 `--strict` 参数让系统在遇到 low 置信度时返回非零退出码，便于 CI/CD 拦截

### 3.3 输出规范

- 输出始终为合法 JSON
- 金额统一为浮点数（保留两位小数）
- 币种统一为 ISO 4217 三字母代码
- 每条结果包含原始文本片段和位置信息，便于追溯

---

## 四、置信度门控机制

### 4.1 判定规则

| 置信度 | 判定条件 | 示例 |
|--------|----------|------|
| `high` | 货币符号明确 + 数字格式无歧义 | `$1,234.56`、`EUR 100` |
| `medium` | 货币符号明确 + 数字格式有轻微歧义（如无小数位） | `¥1000`、`USD 5` |
| `low` | 货币符号明确 + 数字格式存在多解 | `1.234,56`（欧洲 vs 美国格式） |
| `low` | 货币符号缺失，仅凭上下文推断 | `"总价 15000 元"`（"元"非标准代码） |

### 4.2 信息不足时的处理

当系统无法确定某个字段时，**不会编造数据**，而是输出占位符：

```json
{
  "amount": 1234.56,
  "currency": "[需核实:currency]",
  "confidence": "low"
}
```

占位符格式统一为 `[需核实:字段名]`，下游系统可据此触发人工复核流程。

### 4.3 门控建议

- 生产环境建议：`confidence` 为 `low` 的记录不自动入库，进入人工审核队列
- 批量处理时，可先运行一次统计，查看 low 占比，决定是否需要预处理

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入为空 | "输入文本不能为空，请提供至少一个字符。" | 检查输入参数 |
| `E002` | 文件不存在 | "指定的文件路径不存在，请确认路径是否正确。" | 检查文件路径 |
| `E003` | 列名不存在 | "CSV 文件中未找到指定的列名，请检查表头。" | 使用 `--list-columns` 查看可用列 |
| `E004` | 无有效金额 | "未在输入中找到任何可识别的金额，请检查文本格式。" | 确认文本包含货币符号或代码 |
| `E005` | 格式严重歧义 | "检测到多个可能的金额解析结果，请人工确认。" | 使用 `--format-hint` 指定格式（`us`/`eu`） |
| `E006` | 输出文件不可写 | "无法写入输出文件，请检查权限或路径。" | 检查目录权限 |
| `E007` | 编码不支持 | "输入文件编码不是 UTF-8，请转换后重试。" | 使用 `iconv` 转换编码 |

---

## 六、FAQ 反模式对照

### 反模式 1：忽略置信度直接入库

**错误做法**：将所有结果（包括 low 置信度）直接写入数据库。

**正确做法**：设置门控规则，low 置信度记录进入人工审核队列，确认后再入库。

### 反模式 2：假设所有金额都是美元

**错误做法**：看到数字就默认是 USD，不检查货币符号。

**正确做法**：依赖本工具的币种识别能力，未识别出币种时标记为 `[需核实:currency]`。

### 反模式 3：手动处理欧洲数字格式

**错误做法**：遇到 `1.234,56` 就手动替换逗号和点。

**正确做法**：让工具自动识别，或通过 `--format-hint eu` 明确指定格式，避免误判。

### 反模式 4：批量处理前不预览

**错误做法**：直接对整个文件运行，不检查中间结果。

**正确做法**：先取 10 行样本运行，检查输出质量，再全量处理。

### 反模式 5：忽略位置信息

**错误做法**：只取金额数值，丢弃 `position` 字段。

**正确做法**：保留位置信息，便于回溯到原始文本，审计时能快速定位。

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 单条文本
acts as money --input "费用 USD 99.99"

# 文件批量
acts as money --file data.csv --column amount --output result.json

# 自检
acts as money --selftest
```

### 7.2 新手路径（5 分钟）

1. 运行 `acts as money --selftest` 确认安装正确
2. 用 `--input` 测试几条简单文本，观察输出格式
3. 准备一个 CSV 文件，用 `--file` + `--column` 批量处理
4. 查看输出中的 `confidence` 字段，理解不同置信度的含义
5. 对 low 置信度的记录，回到原始文本人工核对

### 7.3 进阶路径（深入使用）

1. **格式歧义处理**：学习欧洲数字格式（`1.234,56` = 1234.56），使用 `--format-hint` 参数
2. **CI/CD 集成**：使用 `--strict` 模式，让 low 置信度导致非零退出码，阻断发布流程
3. **自定义货币扩展**：编辑配置文件 `currencies.json`，添加自定义货币符号
4. **性能优化**：对超大文件（>100MB），使用 `--chunk-size` 参数分块处理
5. **下游对接**：将输出 JSON 直接导入数据库（如 PostgreSQL 的 JSONB 字段）或报表工具（如 Tableau）

---

## 八、技术实现细节

### 8.1 数字格式识别规则

| 格式 | 示例 | 解析结果 | 置信度 |
|------|------|----------|--------|
| 美国格式 | `1,234.56` | 1234.56 | high |
| 欧洲格式 | `1.234,56` | 1234.56 | low（需确认） |
| 无分隔符 | `123456` | 123456.00 | medium |
| 科学计数法 | `1.2e3` | 1200.00 | medium |

### 8.2 支持的币种列表（部分）

| 代码 | 符号 | 名称 |
|------|------|------|
| USD | $ | 美元 |
| EUR | € | 欧元 |
| CNY | ¥ / 元 | 人民币 |
| JPY | ¥ | 日元 |
| GBP | £ | 英镑 |
| CHF | Fr | 瑞士法郎 |
| AUD | A$ | 澳元 |
| CAD | C$ | 加元 |
| HKD | HK$ | 港币 |
| SGD | S$ | 新加坡元 |

完整列表见 `currencies.json`，支持自定义扩展。

### 8.3 正则匹配核心逻辑（伪代码）

```
pattern = 货币符号或代码 + 可选空格 + 数字模式
数字模式 = [0-9]{1,3}([.,][0-9]{3})*([.,][0-9]+)? 或 [0-9]+([.,][0-9]+)?
```

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应自行承担因使用本 Skill 产生的全部责任。本 Skill 仅提供金额提取与标准化功能，不构成任何财务、法律或审计建议。因使用本 Skill 导致的任何直接或间接损失，开发者不承担任何责任。

2. **禁止反向工程**：禁止对本 Skill 进行反向工程、反编译、破解、篡改或试图提取源代码（除非适用法律允许）。禁止将本 Skill 用于任何违反法律法规或平台规定的用途。

3. **数据安全**：使用者应对输入数据的合法性、合规性负责。本 Skill 不存储、不传输任何用户数据至第三方。所有处理均在本地完成。

4. **合规使用**：使用者应确保使用本 Skill 的行为符合当地法律法规及平台规定。因违规使用产生的后果由使用者自行承担。

5. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性的担保。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 DataForge Studio

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

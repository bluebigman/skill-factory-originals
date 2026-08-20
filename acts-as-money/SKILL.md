---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: acts-as-money
name: acts-as-money
displayName: 金额识别 货币解析 数据清洗
description: 从混合文本中提取金额与币种，输出标准化JSON数据，供下游系统直接使用。
version: 1.0.5
rules_version: cpr-20260820-n601
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/acts-as-money
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["acts as money", "金额转换", "货币解析", "money gem", "金额字段处理", "金额提取", "币种识别", "金额标准化"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# acts-as-money — 金额识别与货币解析 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 货币符号识别 | 识别常见货币符号（$、€、£、¥、₩、₹ 等） | `$1,234.56` → USD 1234.56 |
| 货币代码识别 | 识别 ISO 4217 货币代码（USD、EUR、JPY 等） | `EUR 500` → EUR 500.00 |
| 金额数值提取 | 从混合文本中提取相邻的数字片段 | `总价约 3,200 美元` → USD 3200.00 |
| 数字格式解析 | 支持千分位、小数点、欧洲格式（`1.234,56`） | `1.234,56` → 1234.56 |
| 批量处理 | 支持 CSV 文件按列批量提取 | `--file data.csv --column amount` |
| 置信度评估 | 对每条提取结果给出高/中/低置信度 | `"confidence": "high"` |
| 标准化输出 | 输出合法 JSON，可直接供下游系统消费 | 见 §3.3 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不支持非 UTF-8 编码输入 | 输入文本必须为 UTF-8 编码 |
| 不支持语义推断 | 无法判断"大约""可能"等修饰词的实际含义，仅按字面提取 |
| 不支持汇率换算 | 仅提取金额与币种，不做货币兑换 |
| 不支持模糊日期/时间 | 仅处理金额相关字段 |
| 不支持自定义规则脚本 | 如需复杂逻辑，请使用 `--format-hint` 参数或外部后处理 |

### 1.3 适用对象

- **数据工程师**：清洗日志、爬虫数据中的金额字段
- **财务分析师**：从报表、邮件、合同中提取金额信息
- **后端开发者**：将非结构化文本中的金额转为结构化 JSON 供 API 消费
- **运维人员**：在 CI/CD 流水线中校验金额字段格式

---

## 二、触发方式与场景映射

### 2.1 触发词

| 触发词 | 场景 |
|--------|------|
| `acts as money` | 直接调用本 Skill 处理文本 |
| `金额转换` | 中文场景下将金额文本转为标准格式 |
| `货币解析` | 需要从混合文本中分离币种与数值 |
| `money gem` | 兼容旧版调用习惯 |
| `金额字段处理` | 批量处理数据表中的金额列 |
| `金额提取` | 从长文本中抽取金额片段 |
| `币种识别` | 仅需识别币种，不关心具体数值 |
| `金额标准化` | 将多种格式统一为一种标准格式 |

### 2.2 场景映射表

| 用户说（大白话） | 实际执行动作 |
|------------------|--------------|
| "帮我看看这段文本里有多少钱" | 扫描文本，提取所有金额+币种，输出 JSON |
| "这个 CSV 里金额列格式太乱了" | 用 `--file` + `--column` 批量标准化 |
| "这个金额我不确定对不对" | 查看 `confidence` 字段，对 low 置信度人工复核 |
| "CI 里金额格式不对就报错" | 加 `--strict` 参数，low 置信度时返回非零退出码 |
| "欧洲那边的金额格式怎么处理" | 加 `--format-hint european` 参数 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| 运行环境 | Python 3.8+，已安装本 Skill 包 |
| 输入编码 | UTF-8（默认），其他编码需先转码 |
| 输入大小 | 单文件建议 ≤100MB，更大需用 `--chunk-size` |
| 依赖 | 无外部网络依赖，全部本地处理 |

### 3.2 执行步骤

#### 步骤 1：安装确认

```bash
acts as money --selftest
```

预期输出：

```
Self-test passed: 12/12 cases OK
Version: 1.0.0
```

#### 步骤 2：单条文本测试

```bash
echo "The total is $1,234.56 and EUR 500" | acts as money
```

#### 步骤 3：批量处理 CSV

```bash
acts as money --file orders.csv --column amount --output result.json
```

#### 步骤 4：严格模式（CI/CD 用）

```bash
acts as money --file orders.csv --column amount --strict
```

#### 步骤 5：查看置信度并人工复核

```bash
cat result.json | jq '.[] | select(.confidence == "low")'
```

### 3.3 输出规范

输出始终为合法 JSON，结构如下：

```json
{
  "records": [
    {
      "original_text": "The total is $1,234.56 and EUR 500",
      "extractions": [
        {
          "amount": 1234.56,
          "currency": "USD",
          "confidence": "high",
          "matched_fragment": "$1,234.56",
          "needs_review": false
        },
        {
          "amount": 500.00,
          "currency": "EUR",
          "confidence": "high",
          "matched_fragment": "EUR 500",
          "needs_review": false
        }
      ]
    }
  ],
  "summary": {
    "total_records": 1,
    "total_extractions": 2,
    "low_confidence_count": 0
  }
}
```

#### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `amount` | number | 标准化后的数值，保留两位小数 |
| `currency` | string | ISO 4217 货币代码 |
| `confidence` | string | `high` / `medium` / `low` |
| `matched_fragment` | string | 原始文本中匹配到的片段 |
| `needs_review` | boolean | 当 confidence 为 low 时为 `true` |

#### 置信度判定规则

| 置信度 | 判定条件 |
|--------|----------|
| `high` | 货币符号/代码明确 + 数字格式无歧义（如 `$1,234.56`） |
| `medium` | 货币符号明确但数字格式有歧义（如 `1.234` 可能是 1.234 或 1234） |
| `low` | 货币符号缺失或数字格式严重歧义（如 `1234` 无任何货币标识） |

---

## 四、置信度门控

### 4.1 信息不足时的处理

当系统无法确定金额或币种时，**不会编造数据**，而是输出占位符：

```json
{
  "amount": "[需核实:金额]",
  "currency": "[需核实:币种]",
  "confidence": "low",
  "needs_review": true
}
```

### 4.2 人工复核建议

对 `needs_review: true` 的记录：

1. 回到原始文本，查看 `matched_fragment` 对应的上下文
2. 确认数字格式（千分位、小数点位置）
3. 确认币种符号/代码是否被误识别
4. 修正后重新运行，或手动编辑输出 JSON

### 4.3 严格模式

```bash
acts as money --input "unknown amount 1234" --strict
```

退出码：`1`（非零），表示存在 low 置信度记录，可用于 CI/CD 拦截。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入为空 | `Error: Empty input. Please provide text or file.` | 检查输入参数，确保传入非空文本 |
| `E002` | 文件不存在 | `Error: File not found: <path>` | 检查文件路径是否正确 |
| `E003` | 编码错误 | `Error: Invalid UTF-8 encoding in input.` | 将输入转为 UTF-8 编码后重试 |
| `E004` | 列不存在 | `Error: Column '<name>' not found in CSV.` | 用 `--list-columns` 查看可用列 |
| `E005` | 格式提示无效 | `Error: Invalid format-hint. Use 'european' or 'us'.` | 检查 `--format-hint` 参数值 |
| `E006` | 严格模式触发 | `Error: Low confidence records found. Exiting with code 1.` | 查看输出中的 low 置信度记录，人工复核 |
| `E007` | 文件过大 | `Error: File size exceeds limit. Use --chunk-size.` | 添加 `--chunk-size 10000` 分块处理 |
| `E008` | 配置文件错误 | `Error: Invalid currencies.json format.` | 检查自定义货币配置文件格式 |

---

## 六、FAQ 反模式对照

### 6.1 常见坑与反模式

| 坑 | 反模式（错误做法） | 正模式（正确做法） |
|----|-------------------|-------------------|
| **忽略置信度** | 直接使用所有提取结果，不看 `confidence` 字段 | 对 low 置信度记录一律人工复核 |
| **格式假设** | 假设所有数字都是 `1,234.56` 美式格式 | 使用 `--format-hint` 明确指定格式 |
| **币种混淆** | 看到 `$` 就认为是美元 | 结合上下文判断，或用 `--currency-hint` 指定 |
| **批量盲跑** | 对 10 万行 CSV 直接跑，不抽样验证 | 先抽 100 行测试，确认格式后再全量跑 |
| **忽略退出码** | 在 CI 中不检查退出码 | 使用 `--strict` 并检查退出码 |

### 6.2 反模式示例

**反模式 1：不检查置信度**

```bash
# 错误：直接消费所有结果
acts as money --file data.csv --column amount | jq '.records[].extractions[].amount' > amounts.txt
```

**正模式：**

```bash
# 正确：先分离 low 置信度记录
acts as money --file data.csv --column amount --output result.json
jq '.records[] | select(.extractions[].needs_review == true)' result.json > review_list.json
# 人工复核 review_list.json 后再合并
```

**反模式 2：欧洲格式当美式处理**

```bash
# 错误：默认美式格式
echo "1.234,56" | acts as money
# 输出 amount: 1.234（错误）
```

**正模式：**

```bash
# 正确：指定欧洲格式
echo "1.234,56" | acts as money --format-hint european
# 输出 amount: 1234.56（正确）
```

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 单条文本
echo "$1,234.56" | acts as money

# 文件批量
acts as money --file data.csv --column amount --output result.json

# 严格模式（CI 用）
acts as money --file data.csv --column amount --strict

# 欧洲格式
acts as money --input "1.234,56" --format-hint european

# 查看帮助
acts as money --help
```

### 7.2 新手路径（5 分钟）

1. 运行 `acts as money --selftest` 确认安装
2. 用 `echo` 测试 3-5 条简单文本，观察输出格式
3. 准备一个小 CSV（100 行以内），用 `--file` + `--column` 处理
4. 查看输出中的 `confidence` 字段，理解不同置信度的含义
5. 对 low 置信度的记录，回到原始文本人工核对

### 7.3 进阶路径（30 分钟）

1. **格式歧义处理**：学习欧洲数字格式（`1.234,56` = 1234.56），使用 `--format-hint` 参数
2. **CI/CD 集成**：使用 `--strict` 模式，让 low 置信度导致非零退出码，阻断发布流程
3. **自定义货币扩展**：编辑配置文件 `currencies.json`，添加自定义货币符号
4. **性能优化**：对超大文件（>100MB），使用 `--chunk-size` 参数分块处理
5. **下游对接**：将输出 JSON 直接导入数据库（如 PostgreSQL 的 JSONB 字段）或报表工具（如 Tableau）

---

## 八、参数参考

### 8.1 完整参数表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | string | 无 | 直接输入文本（与管道二选一） |
| `--file` | string | 无 | 输入文件路径（CSV 或 TXT） |
| `--column` | string | 无 | CSV 中要处理的列名 |
| `--output` | string | stdout | 输出 JSON 文件路径 |
| `--format-hint` | string | `us` | 数字格式：`us` / `european` |
| `--currency-hint` | string | 无 | 指定默认币种（当文本无货币标识时使用） |
| `--strict` | boolean | `false` | 严格模式，low 置信度时返回非零退出码 |
| `--chunk-size` | int | 0（不分块） | 分块处理的行数 |
| `--list-columns` | boolean | `false` | 列出 CSV 的所有列名 |
| `--selftest` | boolean | `false` | 运行自检 |
| `--version` | boolean | `false` | 显示版本号 |
| `--config` | string | `currencies.json` | 自定义货币配置文件路径 |

### 8.2 自定义货币配置示例

```json
{
  "custom_currencies": [
    {
      "symbol": "₿",
      "code": "BTC",
      "name": "Bitcoin"
    },
    {
      "symbol": "Ξ",
      "code": "ETH",
      "name": "Ethereum"
    }
  ]
}
```

---

## 九、数据安全与合规

### 9.1 数据安全

- 本 Skill **不存储、不传输**任何用户数据至第三方
- 所有处理均在本地完成，无网络请求
- 输入数据不会写入日志文件

### 9.2 合规使用

- 使用者应确保使用本 Skill 的行为符合当地法律法规及平台规定
- 因违规使用产生的后果由使用者自行承担

### 9.3 无担保声明

本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性的担保。

---

## 用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于因数据提取错误、格式误判、置信度误读等导致的任何直接或间接损失。

2. **禁止反向工程**：使用者不得对本 Skill 进行反向工程、反编译、破解或试图获取其源代码（除非明确开源许可）。

3. **数据合规**：使用者应对输入数据的合法性、合规性负责。本 Skill 不存储、不传输任何用户数据至第三方。所有处理均在本地完成。

4. **合规使用**：使用者应确保使用本 Skill 的行为符合当地法律法规及平台规定。因违规使用产生的后果由使用者自行承担。

5. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性的担保。

---

## 许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2026 原创作者（自持版权）

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

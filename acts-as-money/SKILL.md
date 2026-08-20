---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: acts-as-money
name: acts-as-money
displayName: 财务文本 金额提取 货币标准化
description: 从混合文本中提取金额与币种，输出标准化JSON数据，供下游系统直接使用。
version: 1.0.6
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
trigger_words: ["acts as money", "金额转换", "货币解析", "money gem", "金额字段处理", "金额识别", "币种提取", "货币标准化"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# acts-as-money — 金额与币种智能提取工具

## 一、能力边界速查卡

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 金额提取 | 从自然语言、表格、日志中识别金额数字 | "费用总计12,500元" → 12500.00 |
| 币种识别 | 识别货币符号、ISO代码、中文币种名 | "$100" / "USD 100" / "100美元" |
| 格式解析 | 处理千分位、小数点、欧洲数字格式 | "1.234,56" → 1234.56 |
| 批量处理 | 支持CSV/JSON文件批量提取 | `--file input.csv --column amount` |
| 置信度输出 | 每条结果附带置信度评分 | confidence: 0.95 / 0.60 |
| 自定义扩展 | 支持添加自定义货币符号 | 编辑 `currencies.json` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不做语义理解 | 无法判断"大约""左右"等修饰词的实际影响 |
| 不做汇率换算 | 仅提取金额与币种，不进行货币转换 |
| 不做日期识别 | 不处理与金额相邻的日期信息 |
| 不做上下文推断 | 不根据上下文猜测缺失的币种 |
| 不做OCR识别 | 仅处理文本输入，不处理图片 |

### 1.3 适用对象

- 财务人员：处理报销单、发票、银行对账单
- 数据分析师：清洗含金额的混合文本数据
- 开发者：需要将金额字段标准化的API服务
- 运营人员：整理电商订单金额、跨境交易记录

---

## 二、触发方式与场景映射

### 2.1 触发词

直接使用以下任一触发词即可激活：

- `acts as money`
- `金额转换`
- `货币解析`
- `money gem`
- `金额字段处理`
- `金额识别`
- `币种提取`
- `货币标准化`

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 推荐命令 |
|-----------------|---------|---------|
| "帮我看看这段文字里有多少钱" | 提取金额与币种 | `acts as money "报销单总计$1,200.50"` |
| "这个表格里的金额格式太乱了" | 批量标准化金额列 | `acts as money --file data.csv --column amount` |
| "欧洲那边的数字格式看不懂" | 解析欧洲数字格式 | `acts as money --format-hint european "1.234,56 EUR"` |
| "怎么确认提取结果准不准" | 查看置信度评估 | `acts as money --verbose "约100元"` |
| "上线前想自动检查金额格式" | CI/CD集成校验 | `acts as money --strict --file data.csv` |

---

## 三、标准操作流程

### 3.1 前置条件

| 条件 | 要求 | 验证方式 |
|------|------|---------|
| 安装确认 | 已正确安装本Skill | 运行 `acts as money --selftest` |
| 输入格式 | 文本或CSV/JSON文件 | 文件编码为UTF-8 |
| 依赖环境 | Python 3.8+ | `python --version` |
| 配置检查 | 默认配置可用 | 检查 `currencies.json` 存在 |

### 3.2 执行步骤

#### 步骤一：基础测试

```bash
# 运行自检
acts as money --selftest

# 简单文本测试
echo "The total is $1,234.56" | acts as money
echo "费用共计12,500元人民币" | acts as money
echo "Price: 1.234,56 EUR" | acts as money --format-hint european
```

#### 步骤二：单条文本处理

```bash
# 直接传入文本
acts as money "订单金额：USD 899.99，运费$20"

# 输出示例
{
  "matched_fragment": "USD 899.99",
  "amount": 899.99,
  "currency": "USD",
  "confidence": 0.98,
  "format": "decimal_dot"
}
```

#### 步骤三：批量文件处理

```bash
# 处理CSV文件中的指定列
acts as money --file orders.csv --column amount

# 处理JSON文件
acts as money --file data.json --column price

# 分块处理大文件
acts as money --file large.csv --column amount --chunk-size 10000
```

#### 步骤四：结果验证

```bash
# 查看详细输出（含上下文）
acts as money --verbose "约100元"

# 严格模式（低置信度返回非零退出码）
acts as money --strict --file data.csv
echo $?  # 0=全部高置信度, 1=存在低置信度
```

### 3.3 输出规范

#### 标准输出格式（JSON）

```json
{
  "results": [
    {
      "matched_fragment": "原始匹配片段",
      "amount": 1234.56,
      "currency": "CNY",
      "currency_symbol": "¥",
      "confidence": 0.95,
      "format": "decimal_dot",
      "position": {"start": 12, "end": 25},
      "context": "匹配片段前后的文本"
    }
  ],
  "summary": {
    "total_records": 100,
    "high_confidence": 85,
    "medium_confidence": 10,
    "low_confidence": 5,
    "processing_time_ms": 234
  }
}
```

#### 置信度等级说明

| 等级 | 置信度范围 | 含义 | 建议操作 |
|------|-----------|------|---------|
| 高 | 0.90-1.00 | 格式清晰，币种明确 | 直接使用 |
| 中 | 0.70-0.89 | 存在轻微歧义 | 人工复核 |
| 低 | 0.00-0.69 | 格式混乱或币种不明 | 必须人工处理 |

---

## 四、置信度门控机制

### 4.1 信息不足时的处理

当遇到以下情况时，系统不会编造数据，而是输出占位符：

| 场景 | 输出示例 |
|------|---------|
| 币种缺失 | `{"amount": 100, "currency": "[需核实:币种]", "confidence": 0.45}` |
| 金额格式歧义 | `{"amount": "[需核实:金额]", "currency": "USD", "confidence": 0.30}` |
| 数字与文本混合 | `{"amount": "[需核实:金额]", "currency": "[需核实:币种]", "confidence": 0.15}` |

### 4.2 人工核实流程

1. 查看 `matched_fragment` 对应的原始上下文
2. 确认数字格式（千分位、小数点位置）
3. 确认币种符号/代码是否被误识别
4. 修正后重新运行，或手动编辑输出 JSON

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|---------|---------|---------|
| E001 | 输入为空 | "未检测到输入文本，请提供有效内容" | 检查输入参数 |
| E002 | 文件不存在 | "无法找到指定文件，请检查路径" | 确认文件路径正确 |
| E003 | 列名不存在 | "CSV中未找到指定列名" | 使用 `--list-columns` 查看可用列 |
| E004 | 格式解析失败 | "无法解析数字格式，请检查格式提示" | 尝试不同 `--format-hint` |
| E005 | 币种无法识别 | "无法识别币种符号，请检查自定义配置" | 在 `currencies.json` 中添加 |
| E006 | 文件编码错误 | "文件编码不支持，请转换为UTF-8" | 使用 `iconv` 转换编码 |
| E007 | 内存不足 | "文件过大，请使用分块处理" | 添加 `--chunk-size` 参数 |
| E008 | 严格模式失败 | "存在低置信度结果，已阻止流程" | 人工处理低置信度记录后重试 |

---

## 六、常见陷阱与反模式

### 6.1 陷阱一：千分位与小数点混淆

**错误做法**：直接按 `,` 和 `.` 的固定规则解析

**正确做法**：使用 `--format-hint` 指定格式

```bash
# 错误：将 "1,234" 解析为 1.234
# 正确：根据地区指定格式
acts as money --format-hint us "1,234"      # 1234
acts as money --format-hint european "1,234" # 1.234
```

### 6.2 陷阱二：忽略上下文中的币种信息

**错误做法**：只匹配数字，忽略前后文本

**正确做法**：利用上下文提升置信度

```bash
# 错误：只提取数字 100
# 正确：结合上下文识别币种
acts as money "费用：100美元"  # 识别为USD
```

### 6.3 陷阱三：对低置信度结果直接使用

**错误做法**：不检查置信度，直接使用所有结果

**正确做法**：设置置信度阈值，低置信度人工处理

```bash
# 使用 --strict 模式自动拦截低置信度
acts as money --strict --min-confidence 0.8 --file data.csv
```

### 6.4 陷阱四：忽略欧洲数字格式

**错误做法**：假设所有地区使用相同数字格式

**正确做法**：根据数据来源指定格式

```bash
# 欧洲格式：1.234,56 表示 1234.56
acts as money --format-hint european "1.234,56 EUR"
```

### 6.5 陷阱五：批量处理前不预览

**错误做法**：直接对全量数据运行，不检查样本

**正确做法**：先处理小样本，确认格式后再全量运行

```bash
# 先处理前10行
head -10 data.csv | acts as money --file - --column amount
# 确认无误后全量处理
acts as money --file data.csv --column amount
```

---

## 七、进阶使用指南

### 7.1 自定义货币扩展

编辑 `currencies.json` 文件：

```json
{
  "custom_currencies": [
    {
      "symbol": "₿",
      "code": "BTC",
      "name": "Bitcoin",
      "decimal_places": 8
    }
  ]
}
```

### 7.2 CI/CD 集成

```yaml
# GitHub Actions 示例
- name: Validate Amounts
  run: |
    acts as money --strict --file data.csv --column amount
  env:
    MIN_CONFIDENCE: 0.85
```

### 7.3 性能优化

| 场景 | 推荐参数 | 说明 |
|------|---------|------|
| 大文件处理 | `--chunk-size 50000` | 分块处理，降低内存占用 |
| 实时API | `--no-write` | 不写入日志，提升速度 |
| 多线程 | `--workers 4` | 并行处理，提升吞吐量 |

### 7.4 下游系统对接

```python
# PostgreSQL JSONB 导入示例
import json
import psycopg2

with open('output.json') as f:
    data = json.load(f)

conn = psycopg2.connect("dbname=finance")
cur = conn.cursor()
for result in data['results']:
    cur.execute(
        "INSERT INTO amounts (data) VALUES (%s)",
        (json.dumps(result),)
    )
conn.commit()
```

---

## 八、分层次阅读路径

### 8.1 新手快速上手（5分钟）

1. 运行 `acts as money --selftest` 确认安装
2. 用 `echo` 测试 3-5 条简单文本，观察输出格式
3. 准备一个小 CSV（100 行以内），用 `--file` + `--column` 处理
4. 查看输出中的 `confidence` 字段，理解不同置信度的含义
5. 对 low 置信度的记录，回到原始文本人工核对

### 8.2 进阶用户（30分钟）

1. 学习欧洲数字格式处理：`--format-hint european`
2. 配置自定义货币：编辑 `currencies.json`
3. 设置严格模式：`--strict --min-confidence 0.8`
4. 集成到 CI/CD 流程
5. 对接下游数据库或报表工具

### 8.3 高级用户（按需）

1. 性能调优：`--chunk-size`、`--workers` 参数组合
2. 自定义输出格式：使用 `--output-template` 定制 JSON 结构
3. 编写自动化脚本：结合 Python/Shell 实现全流程自动化
4. 扩展功能：基于输出结果构建数据校验规则

---

## 九、隐私与安全说明

- 所有处理均在本地完成，不传输任何数据至第三方
- 输入数据不会写入日志文件
- 输出结果仅保存在用户指定的位置
- 建议对敏感数据使用加密存储

---

## 用户协议

<!-- user-agreement-injected -->

**生效日期**：2026年1月1日

**1. 责任承担**
使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于因数据提取错误、格式误判、置信度误读等导致的任何直接或间接损失。

**2. 禁止反向工程**
使用者不得对本 Skill 进行反向工程、反编译、破解或试图获取其源代码（除非明确开源许可）。

**3. 数据合规**
使用者应对输入数据的合法性、合规性负责。本 Skill 不存储、不传输任何用户数据至第三方。所有处理均在本地完成。

**4. 合规使用**
使用者应确保使用本 Skill 的行为符合当地法律法规及平台规定。因违规使用产生的后果由使用者自行承担。

**5. 无担保声明**
本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性的担保。

---

## 许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 LinguaForge

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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: stock-option-analysis
name: stock-option-analysis
displayName: 期权估值 行权决策 希腊字母分析
description: 输入期权参数，自动完成估值、风险度量与行权策略建议。
version: 2.64.2
rules_version: cpr-20260817-n526
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/stock-option-analysis
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: QuantForge Studio
agent_created: true
trigger_words: ["期权估值", "权证分析", "希腊字母", "行权策略", "option pricing", "期权定价", "Black-Scholes"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 期权估值与行权决策助手（SKILL.md）

## 一、能力边界与适用对象（一页纸速查卡）

本 Skill 面向金融从业者、量化爱好者及个人投资者，提供**欧式期权/权证**的快速估值与策略参考。它不是一个交易终端，也不替代专业风控系统。

### 1.1 能做什么（✅）

| 功能模块 | 说明 | 输入示例 |
|---------|------|---------|
| 参数解析 | 接受结构化参数或自然语言描述 | `S=100, K=105, T=0.5, r=0.03, sigma=0.2` 或 "股价100，行权价105，半年后到期，无风险利率3%，波动率20%" |
| 估值计算 | 基于 Black-Scholes 模型计算看涨/看跌期权理论价格 | 自动识别 Call/Put |
| 希腊字母 | 输出 Delta、Gamma、Theta、Vega、Rho 五项风险指标 | 自动计算 |
| 内在价值与时间价值 | 拆分期权价格构成 | 自动计算 |
| 策略建议 | 基于 Delta 与内在价值给出方向性参考 | 输出"实值/平值/虚值"状态与行权倾向 |
| 批量处理 | 读取 CSV 文件批量计算 | `data/sample_options.csv` |
| 自检与版本 | 验证环境与模型正确性 | `--selftest` / `--version` |

### 1.2 不能做什么（❌）

- 不支持美式期权提前行权的最优停时计算（仅提供参考性建议）
- 不包含股息率参数（若需考虑股息，请自行调整 S 或使用扩展模型）
- 不提供投资建议或收益承诺——所有输出均为数学计算结果，非买卖指令
- 不处理奇异期权（障碍、亚式、回望等）
- 不连接实时行情，所有输入需用户自行提供

### 1.3 适用对象

- 持有期权/权证仓位，需要快速评估当前价值的投资者
- 学习金融工程，需要验证手算结果的在校学生
- 需要批量估算期权组合风险的量化研究员

---

## 二、触发方式与场景映射

### 2.1 触发词

当你的对话中出现以下任一词汇或短语时，本 Skill 将被激活：

- **核心触发**：期权估值、权证分析、希腊字母、行权策略、option pricing
- **同义补充**：期权定价、Black-Scholes 计算、期权风险指标、行权决策辅助

### 2.2 大白话场景映射表

| 用户可能说… | 本 Skill 理解… | 执行动作 |
|------------|---------------|---------|
| "帮我看看这个期权值多少钱" | 需要估值计算 | 解析参数 → 计算价格 → 输出结果 |
| "股价50，行权价55，3个月到期，利率2%，波动率25%，是看涨" | 自然语言参数输入 | 提取 S/K/T/r/sigma → 计算 Call 价格 |
| "我的权证 Delta 是多少？" | 需要希腊字母 | 计算 Delta 并解释含义 |
| "这期权该不该行权？" | 需要策略参考 | 输出实值状态 + 时间价值占比 + 建议 |
| "批量算一下这些期权" | 需要 CSV 批处理 | 读取文件 → 逐行计算 → 汇总输出 |

---

## 三、标准执行流程

### 3.1 前置条件

- Python 3.8+ 环境，已安装 `numpy`、`scipy`、`pandas`（CLI 模式）
- 输入参数完整且符合数值范围（见 3.2 参数校验表）
- 若使用自然语言输入，需包含至少 4 个核心参数（S、K、T、sigma）

### 3.2 参数校验表

| 参数 | 符号 | 允许范围 | 必填 | 说明 |
|------|------|---------|------|------|
| 标的资产价格 | S | > 0 | ✅ | 当前股价/标的指数 |
| 行权价 | K | > 0 | ✅ | 期权合约约定的执行价格 |
| 剩余期限 | T | > 0, ≤ 10 年 | ✅ | 以年为单位（0.5 = 半年） |
| 无风险利率 | r | ≥ 0, ≤ 0.20 | ✅ | 年化连续复利利率 |
| 波动率 | sigma | > 0, ≤ 2.0 | ✅ | 年化波动率（20% = 0.2） |
| 期权类型 | type | call / put | ✅ | 看涨或看跌 |
| 批量文件路径 | --file | 合法 CSV 路径 | ❌ | 包含上述字段的 CSV |

### 3.3 执行步骤（分步编号）

1. **参数接收与解析**
   - 若为 CLI 参数：直接读取 `--S`、`--K`、`--T`、`--r`、`--sigma`、`--type`
   - 若为自然语言：调用内置解析器提取数值与期权类型关键词
   - 若为 CSV：读取文件并逐行映射字段

2. **参数校验**
   - 逐项检查 3.2 表范围，任一不满足即返回错误码 `E1001`~`E1005`
   - 校验失败时，输出错误说明与正确格式示例，终止计算

3. **模型计算**
   - 计算 `d1 = (ln(S/K) + (r + 0.5*sigma²)*T) / (sigma*sqrt(T))`
   - 计算 `d2 = d1 - sigma*sqrt(T)`
   - 看涨期权价格 `C = S*N(d1) - K*exp(-r*T)*N(d2)`
   - 看跌期权价格 `P = K*exp(-r*T)*N(-d2) - S*N(-d1)`
   - 希腊字母按标准 BS 公式推导（见 `docs/technical_spec.md`）

4. **结果组装**
   - 计算内在价值：`max(S-K, 0)`（Call）或 `max(K-S, 0)`（Put）
   - 计算时间价值：期权价格 - 内在价值
   - 判定实值状态：内在价值 > 0 → 实值；= 0 且接近平值 → 平值；否则虚值
   - 生成策略建议（见 3.5 策略建议规则）

5. **输出**
   - 结构化 JSON 或表格形式（CLI 默认表格，`--json` 切换）
   - 包含：价格、五项希腊字母、内在/时间价值、实值状态、策略参考

### 3.4 输出规范

```json
{
  "input": {"S": 100, "K": 105, "T": 0.5, "r": 0.03, "sigma": 0.2, "type": "call"},
  "output": {
    "price": 3.42,
    "intrinsic_value": 0.0,
    "time_value": 3.42,
    "moneyness": "虚值",
    "greeks": {"delta": 0.41, "gamma": 0.03, "theta": -0.05, "vega": 0.28, "rho": 0.12},
    "strategy_note": "虚值看涨期权，时间价值占比100%，不建议行权，可考虑卖出对冲或等待标的上涨"
  },
  "confidence": 0.95,
  "model": "Black-Scholes (European)"
}
```

### 3.5 策略建议规则

| 实值状态 | 时间价值占比 | 建议参考 |
|---------|-------------|---------|
| 实值 (ITM) | < 20% | 行权价值较高，可考虑行权或平仓锁定利润 |
| 实值 (ITM) | 20% ~ 50% | 持有或部分止盈，关注时间价值衰减 |
| 平值 (ATM) | > 80% | 时间价值主导，行权意义不大，考虑对冲或展期 |
| 虚值 (OTM) | 100% | 纯时间价值，不建议行权，需评估标的走势 |

---

## 四、置信度门控

### 4.1 信息不足处理

当输入参数缺失或模糊时，本 Skill **不会猜测**，而是输出 `[需核实:字段名]` 占位符，并提示用户补充。

| 场景 | 输出示例 |
|------|---------|
| 缺少波动率 | `[需核实:sigma] 波动率未提供，无法完成估值。请补充年化波动率（如 0.2 表示 20%）` |
| 期权类型不明 | `[需核实:type] 无法判断看涨/看跌，请明确输入 call 或 put` |
| 自然语言歧义 | `[需核实:T] 剩余期限表述不清，请提供以年为单位的时间（如 0.5 表示半年）` |

### 4.2 置信度评估

- 参数完整且通过校验 → 置信度 ≥ 0.95
- 参数完整但部分为估算值（如用户说"大约"）→ 置信度 0.80，并标注估算字段
- 参数缺失但已用占位符 → 不输出计算结果，仅返回待补清单

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|---------|---------|
| `E1001` | S 不合法 | "标的资产价格必须大于 0" | 检查 S 是否为正值，重新输入 |
| `E1002` | K 不合法 | "行权价必须大于 0" | 检查 K 是否为正值，重新输入 |
| `E1003` | T 不合法 | "剩余期限需在 (0, 10] 年范围内" | 确认 T 以年为单位，如 30 天应输入 30/365≈0.082 |
| `E1004` | r 不合法 | "无风险利率需在 [0, 0.20] 范围内" | 确认 r 为小数形式（3% → 0.03） |
| `E1005` | sigma 不合法 | "波动率需在 (0, 2.0] 范围内" | 确认 sigma 为小数形式（20% → 0.2） |
| `E2001` | 类型无法识别 | "无法识别期权类型，请输入 call 或 put" | 检查输入是否包含明确的方向词 |
| `E3001` | CSV 字段缺失 | "CSV 缺少必要列：S, K, T, r, sigma, type" | 对照 `data/sample_options.csv` 检查表头 |
| `E9001` | 内部计算异常 | "计算过程中出现数值错误，请检查参数是否极端" | 确认参数在合理范围，或运行 `--selftest` 验证环境 |

---

## 六、FAQ 与反模式对照

### 6.1 常见坑（反模式）

| 反模式 | 问题 | 正确做法 |
|--------|------|---------|
| ❌ 输入"3个月"作为 T=3 | T 必须以年为单位，3 会被当作 3 年 | 输入 0.25 或 3/12 |
| ❌ 输入"利率3" 而非 0.03 | 百分比与小数混淆 | 统一使用小数：3% → 0.03 |
| ❌ 忽略股息率 | 标的在 T 内分红时 BS 定价偏高 | 若已知股息率 q，可手动调整 S 或使用扩展模型 |
| ❌ 用 BS 定价美式期权 | BS 仅适用于欧式期权，美式需二叉树/有限差分 | 本 Skill 仅支持欧式，请确认合约类型 |
| ❌ 把策略建议当投资指令 | 策略建议仅为数学参考，不构成买卖依据 | 结合自身风险承受能力独立决策 |

### 6.2 用户高频疑问

**Q1: 为什么我的期权价格和券商软件显示的不一样？**
A: 可能原因：(1) 券商使用隐含波动率而非历史波动率；(2) 券商考虑了股息或借贷利率；(3) 模型差异（二叉树 vs BS）。建议使用 `--sigma` 输入隐含波动率进行对比。

**Q2: Delta 0.5 意味着什么？**
A: 表示标的资产价格每变动 1 元，期权价格理论上变动约 0.5 元。这是瞬时近似值，实际会随 S 变化（Gamma 影响）。

**Q3: 时间价值为什么总是正的？**
A: 在到期前，期权具有时间价值，因为未来存在不确定性，标的可能向有利方向变动。深度虚值期权的时间价值趋近于 0，但通常不为负（欧式期权在极端情况下可能出现负时间价值，但罕见）。

---

## 七、渐进式披露与学习路径

### 7.1 速查卡（30 秒上手）

```
输入格式：S=100, K=105, T=0.5, r=0.03, sigma=0.2, type=call
CLI 示例：python option_pricing.py --S 100 --K 105 --T 0.5 --r 0.03 --sigma 0.2 --type call
输出内容：价格 + 希腊字母 + 内在/时间价值 + 策略参考
```

### 7.2 分层次阅读路径

**新手路径（首次使用）**
1. 阅读本文件「一、能力边界」明确工具定位
2. 使用 `--selftest` 验证环境
3. 用 `data/sample_options.csv` 跑通批量流程
4. 对照「三、标准执行流程」理解每个输出字段含义

**进阶路径（深入应用）**
1. 阅读 `docs/technical_spec.md` 了解模型推导与希腊字母公式
2. 尝试修改 `src/option_pricing.py` 中的波动率模型（如加入 GARCH）
3. 对比不同 sigma 输入对价格与 Delta 的影响
4. 结合自身持仓，用批量模式评估组合风险暴露

---

## 八、CLI 参考与示例

### 8.1 命令速览

```bash
# 查看帮助
python option_pricing.py --help

# 单次计算
python option_pricing.py --S 100 --K 105 --T 0.5 --r 0.03 --sigma 0.2 --type call

# 批量计算
python option_pricing.py --file data/sample_options.csv

# JSON 输出
python option_pricing.py --S 100 --K 105 --T 0.5 --r 0.03 --sigma 0.2 --type put --json

# 自检
python option_pricing.py --selftest

# 版本
python option_pricing.py --version
```

### 8.2 自然语言交互示例

**用户输入**："帮我算一下，股价 50，行权价 55，3 个月到期，无风险利率 2%，波动率 25%，看涨期权"

**Skill 响应**：
```
已解析参数：S=50, K=55, T=0.25, r=0.02, sigma=0.25, type=call
计算结果：
  期权价格：1.23
  内在价值：0.00（虚值）
  时间价值：1.23（占比 100%）
  Delta：0.34 | Gamma：0.05 | Theta：-0.03 | Vega：0.15 | Rho：0.02
  策略参考：虚值看涨期权，纯时间价值，不建议行权。若看多后市可继续持有，但需关注 Theta 衰减。
```

---

## 九、技术实现说明

### 9.1 目录结构

```
stock-option-analysis/
├── SKILL.md              # 本文档
├── src/
│   └── option_pricing.py # 主程序（CLI）
├── data/
│   └── sample_options.csv # 10 组示例数据
├── docs/
│   └── technical_spec.md  # 模型推导与参数校准
└── tests/
    └── test_pricing.py    # 单元测试
```

### 9.2 模型假设

- 标的资产价格服从几何布朗运动（恒定波动率）
- 无交易成本与税收
- 无风险利率恒定
- 期权为欧式（仅到期日可行权）
- 市场无套利机会

---

## 十、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 输出的所有计算结果、策略建议均为数学模型的参考输出，不构成任何投资建议、买卖要约或收益承诺。任何基于本 Skill 输出做出的投资决策，风险由使用者自行承担。

2. **禁止反向工程**：未经授权，不得对本 Skill 的源代码、模型参数、文档内容进行反向工程、反编译、破解或试图提取核心算法用于商业用途。

3. **无担保声明**：本 Skill 按"原样"


## 许可证（License）

```text
MIT License

Copyright (c) 2026 SkillForge Lab

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```
<!-- professional-license-embedded -->

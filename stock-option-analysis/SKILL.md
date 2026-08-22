---
slug: stock-option-analysis
name: stock-option-analysis
displayName: 期权估值 行权决策 风险度量
description: 输入期权参数，输出理论价格、希腊字母与行权策略参考。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: QuantForge Studio
agent_created: true
trigger_words: ["期权估值","权证分析","希腊字母","行权策略","option pricing","期权定价","Black-Scholes"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# 期权估值与行权决策 Skill 文档

## 一、能力边界：一页纸速查卡

本 Skill 面向期权/权证的**理论估值**与**策略参考**，不构成任何投资建议或收益承诺。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入形式 | 结构化参数（S/K/T/r/sigma）或自然语言描述 | 无法处理缺失关键参数（如无行权价）的请求 |
| 计算范围 | 欧式期权 Black-Scholes 定价、内在价值、时间价值、Delta/Gamma/Theta/Vega/Rho | 美式期权提前行权最优边界、奇异期权（障碍/亚式等）定价 |
| 输出内容 | 理论价格、希腊字母数值、置信度评级、行权概率参考 | 不输出买卖指令、不预测标的价格走势 |
| 数据要求 | 需用户提供或确认标的现价、行权价、剩余期限、无风险利率、波动率 | 无法自动获取实时行情，不联网拉取数据 |
| 适用对象 | 期权交易者、风控人员、金融学习者、量化策略开发者 | 非专业用户直接依赖结果做重大资金决策 |

**边界说明**：模型假设标的收益率服从对数正态分布，实际市场存在厚尾、跳跃等特征，结果仅为理论参考。

---

## 二、触发方式：场景映射表

当用户输入包含以下意图时，本 Skill 自动激活：

| 用户大白话 | 触发词命中 | 解析结果 |
|-----------|-----------|---------|
| "帮我算一下这个期权值多少钱" | 期权估值 | 进入参数收集流程 |
| "S=100, K=105, T=0.5, r=0.03, sigma=0.2" | 参数直输 | 直接进入计算 |
| "认购权证现在行权划算吗" | 行权策略 | 计算内在价值+时间价值，给出参考 |
| "这个期权的 Delta 是多少" | 希腊字母 | 输出全部希腊字母 |
| "批量算一下这些期权" | 批量处理 | 读取 CSV 批量计算 |

**参数速查表**：

| 符号 | 含义 | 单位 | 合理范围 | 必填 |
|------|------|------|---------|------|
| S | 标的现价 | 货币单位 | >0 | 是 |
| K | 行权价 | 货币单位 | >0 | 是 |
| T | 剩余期限 | 年 | 0 < T ≤ 5 | 是 |
| r | 无风险利率 | 小数（如0.03=3%） | -0.05 ~ 0.15 | 是 |
| sigma | 年化波动率 | 小数（如0.2=20%） | 0.01 ~ 2.0 | 是 |
| type | 期权类型 | call/put | 二者其一 | 是 |

---

## 三、标准流程：从输入到输出

### 前置条件

1. 用户提供至少 5 个核心参数（S/K/T/r/sigma）及期权类型
2. 若参数缺失，系统进入澄清模式，逐项询问缺失项
3. 参数格式校验通过（数值范围、类型正确）

### 执行步骤

**步骤 1：参数解析与校验**

- 从自然语言中提取参数对（如 "S=100" 或 "标的价格100元"）
- 校验数值范围，非法值返回错误码 `E1001`
- 输出解析后的参数表供用户确认

**步骤 2：估值计算**

- 计算内在价值：
  - Call: max(S - K, 0)
  - Put: max(K - S, 0)
- 计算时间价值 = 期权理论价格 - 内在价值
- 使用 Black-Scholes 公式计算理论价格：
  ```
  d1 = (ln(S/K) + (r + sigma^2/2)*T) / (sigma*sqrt(T))
  d2 = d1 - sigma*sqrt(T)
  Call = S*N(d1) - K*exp(-r*T)*N(d2)
  Put  = K*exp(-r*T)*N(-d2) - S*N(-d1)
  ```
- 计算希腊字母（Delta, Gamma, Theta, Vega, Rho）

**步骤 3：置信度评估**

| 条件 | 置信度 | 说明 |
|------|--------|------|
| 参数完整且波动率为近期历史波动率 | 高 | 结果可直接参考 |
| 波动率为估计值或用户主观给定 | 中 | 建议做敏感性分析 |
| 参数存在冲突或来源不明 | 低 | 输出 [需核实:字段] 提示 |

**步骤 4：策略建议生成**

- 若内在价值 > 0：提示实值状态，行权有内在价值支撑
- 若时间价值 > 内在价值 30%：提示时间价值占比偏高，谨慎持有
- 若 Delta 绝对值 > 0.7：提示标的敏感度高，注意对冲

**步骤 5：输出规范**

输出结构化 JSON 或 Markdown 表格：

```json
{
  "input": {"S":100,"K":105,"T":0.5,"r":0.03,"sigma":0.2,"type":"call"},
  "price": {"theoretical": 3.42, "intrinsic": 0.0, "time_value": 3.42},
  "greeks": {"delta":0.42,"gamma":0.032,"theta":-0.015,"vega":0.18,"rho":0.08},
  "confidence": "medium",
  "strategy_note": "虚值期权，时间价值占比100%，建议关注波动率变化"
}
```

---

## 四、置信度门控：不编造原则

当以下情况出现时，输出 `[需核实:字段名]` 占位符，**绝不猜测**：

| 场景 | 处理方式 |
|------|---------|
| 用户未提供波动率 | 输出 `[需核实:sigma]`，并提示可用历史波动率或隐含波动率 |
| 无风险利率缺失 | 输出 `[需核实:r]`，建议参考同期国债收益率 |
| 剩余期限表述模糊（如"下个月"） | 输出 `[需核实:T]`，请用户明确具体日期 |
| 标的价格为区间而非确定值 | 输出 `[需核实:S]`，并建议使用区间上下限分别计算 |

**示例**：

> 用户输入："算一下这个 call 期权，行权价 50，还有 3 个月到期"
>
> 系统响应："已识别参数 K=50, T=0.25，但缺少 S（标的现价）、r（无风险利率）、sigma（波动率）。请补充：`[需核实:S]`、`[需核实:r]`、`[需核实:sigma]`。参考格式：S=52, r=0.02, sigma=0.25"

---

## 五、错误码体系

| 错误码 | 触发条件 | 提示话术 | 修正步骤 |
|--------|---------|---------|---------|
| E1001 | 参数数值非法（负数、零、超范围） | "参数 S 的值为 -5，必须大于 0" | 检查输入数值，修正后重试 |
| E1002 | 参数类型错误（如 T 传了字符串） | "参数 T 应为数字，收到 '三个月'" | 将时间转换为年（3个月=0.25年） |
| E1003 | 缺少必填参数 | "缺少参数 sigma（波动率），无法计算" | 补充缺失参数或使用默认值（需明确告知） |
| E1004 | 期权类型无法识别 | "无法识别期权类型，请输入 call 或 put" | 明确指定类型 |
| E1005 | 批量文件格式错误 | "CSV 第 3 行缺少 K 列" | 检查 CSV 表头，确保包含 S,K,T,r,sigma,type |
| E1006 | 计算发散（sigma 过小导致除零） | "波动率过小导致计算不稳定，请检查 sigma" | 确认 sigma > 0.001 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正确模式 |
|--------|-------------------|---------|
| 忽略波动率来源 | 直接使用用户给的 sigma 不做校验 | 询问波动率是历史波动率还是隐含波动率，并标注置信度 |
| 混淆内在价值与理论价格 | 把 max(S-K,0) 当作期权价格 | 明确区分：内在价值是下限，理论价格包含时间价值 |
| 对虚值期权建议行权 | 虚值期权建议"立即行权" | 虚值期权行权无意义，建议关注标的走势或平仓 |
| 忽略利率影响 | 长期期权忽略 r 的变化 | 对 T>1 的期权，提示利率敏感性（Rho） |
| 批量处理不检查数据质量 | 直接计算 CSV 中所有行 | 先做数据清洗，剔除缺失或异常行，输出处理日志 |

---

## 七、渐进式披露：分层次阅读路径

### 速查卡（30 秒上手）

```
输入格式：S=100, K=105, T=0.5, r=0.03, sigma=0.2, type=call
或自然语言："计算行权价105、半年到期、波动率20%的看涨期权"
输出：理论价格 + 希腊字母 + 置信度 + 策略参考
```

### 新手路径（5 分钟理解）

1. 阅读「能力边界」了解工具限制
2. 用「触发方式」中的示例输入尝试一次计算
3. 查看输出中的「策略建议」字段，理解内在价值与时间价值
4. 遇到错误时对照「错误码体系」修正输入

### 进阶路径（深度使用）

1. 阅读 `docs/technical_spec.md` 了解模型推导与参数校准方法
2. 使用 `data/sample_options.csv` 测试批量处理功能
3. 对同一期权做敏感性分析（改变 sigma 或 T，观察价格变化）
4. 结合希腊字母构建 Delta 中性对冲策略参考

---

## 八、命令行工具说明

在 `src/` 目录下运行：

```bash
# 查看帮助
python option_pricing.py --help

# 单次计算
python option_pricing.py --S 100 --K 105 --T 0.5 --r 0.03 --sigma 0.2 --type call

# 批量计算
python option_pricing.py --file ../data/sample_options.csv

# 自检
python option_pricing.py --selftest

# 版本
python option_pricing.py --version
```

---

## 九、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 输出的所有数值、策略建议均为理论参考，不构成投资建议。实际投资决策需结合个人风险承受能力、市场状况等因素独立判断。
2. **禁止反向工程**：不得对本 Skill 的代码、文档、算法进行反向工程、反编译、破解或试图提取底层逻辑用于商业竞争。
3. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性。
4. **使用限制**：不得将本 Skill 用于非法目的、欺诈行为或任何违反适用法律法规的活动。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

本 Skill 采用 MIT 许可证授权：

```
MIT License

Copyright (c) 2024 QuantForge Studio

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*

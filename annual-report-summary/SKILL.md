---
slug: annual-report-summary
name: annual-report-summary
displayName: 年报速读 财务透视 决策简报
description: 从年报文本中提取关键财务指标（ROE/净利润/营收/现金流等）并生成结构化决策简报，支持JSON输出与自检。
version: 2.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: FinSight Studio
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，仅供学习参考，不构成投资建议。
author: FinSight Studio
agent_created: true
trigger_words: ["年报解读", "财报分析", "年度报告摘要", "财务数据提炼", "投资决策支持", "年报速读"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# 年报速读 · 财务透视 · 决策简报

## 一、能力边界（真实实现）

### 1.1 能做什么（代码已验证）

| 编号 | 能力项 | 实现方式 | 输出示例 |
|------|--------|----------|----------|
| C01 | 提取ROE（净资产收益率） | 正则匹配6种写法（含加权/扣非/括号标注） | `ROE: 15.2%` |
| C02 | 提取净利润增长率 | 正则匹配4种表述（增长率/同比/同比增长/同比变化） | `净利润增长率: 23.5%` |
| C03 | 提取营业收入及增长率 | 正则匹配营收/营业收入+金额/增长率 | `营收: 12.3亿, 增长率: 18.2%` |
| C04 | 提取毛利率 | 正则匹配毛利率/销售毛利率 | `毛利率: 35.7%` |
| C05 | 提取净利率 | 正则匹配净利率/销售净利率 | `净利率: 12.1%` |
| C06 | 提取资产负债率 | 正则匹配资产负债率 | `资产负债率: 58.3%` |
| C07 | 提取经营现金流净额 | 正则匹配经营/经营性现金流净额 | `经营现金流: 8.5亿` |
| C08 | 提取每股收益(EPS) | 正则匹配每股收益/基本每股收益 | `EPS: 1.25元` |
| C09 | 提取研发费用率 | 正则匹配研发费用率/研发投入占比 | `研发费用率: 7.2%` |
| C10 | 提取商誉金额 | 正则匹配商誉/商誉账面价值 | `商誉: 3.2亿` |
| C11 | 提取审计意见类型 | 正则匹配审计意见（标准/保留/否定/无法表示） | `审计意见: 标准无保留` |
| C12 | 生成结构化JSON摘要 | 汇总所有提取结果+时间戳+置信度 | `{"roe": "15.2%", ...}` |

### 1.2 不能做什么（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| X01 | 不提供投资建议 | 不判断买卖时机，不给出目标价 |
| X02 | 不预测未来业绩 | 不基于历史数据外推未来盈利 |
| X03 | 不验证数据真实性 | 仅做文本提取，不核实年报数据 |
| X04 | 不处理PDF/扫描件 | 仅支持纯文本输入 |
| X05 | 不比较同行业公司 | 除非用户主动提供可比数据 |
| X06 | 不计算复合增长率 | 不自动计算CAGR，仅提取文本中已有数值 |

### 1.3 适用对象

- 个人投资者：快速了解持仓标的财务健康度
- 财务分析师：初步筛选工具，定位需深挖科目
- 财经记者：撰写年报快讯前的数据核对清单
- 企业战略人员：对标同行年报关键指标

## 二、触发条件

### 2.1 自动触发关键词

## 许可证（License）

```text
MIT License

Copyright (c) {year} {holder}

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

## 失败处理

- 命令执行失败或返回非零退出码时，程序会输出明确错误信息并给出排查建议。
- 依赖缺失时提示安装命令；网络异常时建议重试并检查连接。
- 异常情况不中断主流程，错误信息包含具体原因（error context），便于定位修复。
## 前置条件

- 本技能开箱即用，无需额外安装依赖。
- 需要 Python 3.9+ 运行环境。
- 涉及网络请求时需保持网络连通。
## 执行步骤

1. 读取输入参数或交互输入。
2. 按技能定义的处理流程执行核心逻辑。
3. 输出结构化结果，并在完成后给出下一步建议。
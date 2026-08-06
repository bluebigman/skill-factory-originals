---
slug: house-purchase-plan
name: house-purchase-plan
displayName: 购房测算 月供评估 预算规划
description: 输入收入与房价，输出月供、税费、现金流压力与购房建议。
version: 3.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 居安测算工坊
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 居安测算工坊
agent_created: true
trigger_words: ["house-purchase-plan", "买房测算", "月供计算", "购房预算", "房贷方案对比", "置业评估", "按揭压力测试"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# 购房测算 Skill 使用指南

## 一、能力边界（一页纸速查卡）

### 1.1 本 Skill 能做什么（真实实现）

| 序号 | 能力项 | 说明 | 对应函数 |
|------|--------|------|----------|
| 1 | 月供估算 | 基于贷款金额、期限、利率（LPR+基点）计算等额本息/等额本金月供 | `calculate_monthly_payment()` |
| 2 | 税费概算 | 契税、个税、增值税、中介费、维修基金等常规费用估算 | `calculate_taxes()` |
| 3 | 现金流压力评估 | 对比月供与家庭月收入，输出负债收入比（DTI）与安全边际 | `assess_cashflow()` |
| 4 | 购房建议生成 | 根据首付比例、利率浮动、收入水平给出方向性建议 | `generate_advice()` |
| 5 | 方案对比 | 支持多组参数并列输入，输出对比表格 | `compare_scenarios()` |
| 6 | 利率查询 | 通过API获取最新LPR（含超时与重试） | `fetch_lpr()` |
| 7 | 自检 | 运行内置测试验证核心函数正确性 | `selftest()` |

### 1.2 本 Skill 不能做什么（明确限制）

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不提供法律意见 | 涉及产权纠纷、合同条款解释请咨询律师 |
| 2 | 不做投资回报预测 | 不预测房价涨跌、租金收益率、资产增值 |
| 3 | 不替代银行审批 | 实际贷款额度、利率以银行最终审批为准 |
| 4 | 不覆盖所有城市政策 | 限购、限贷、公积金政策因城市而异，需人工核对 |
| 5 | 不处理非住宅类房产 | 商铺、写字楼、厂房等不在本工具范围内 |
| 6 | 不保证LPR实时性 | 若API不可用，使用默认值并明确提示 |

### 1.3 适用对象

- 首次购房的工薪家庭
- 考虑换房的改善型买家
- 需要快速比较不同贷款方案的个人
- 房产中介或金融顾问的初步测算辅助

## 二、触发条件

当用户输入包含以下关键词时，自动触发本Skill：

- 买房测算、月供计算、购房预算
- 房贷方案对比、置业评估、按揭压力测试
- 输入包含房价、收入、首付比例等参数

## 三、标准流程（Workflow）

### 3.1 输入参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--price` | float | 是 | - | 房屋总价（万元） |
| `--income` | float | 是 | - | 家庭月收入（元） |
| `--down-payment-ratio` | float | 否 | 0.30 | 首付比例（0-1） |
| `--loan-years` | int | 否 | 30 | 贷款年限（年） |
| `--lpr` | float | 否 | 3.85 | 5年期以上LPR（%） |
| `--bp` | int | 否 | 30 | 利率加点（基点） |
| `--method` | str | 否 | equal_installment | 还款方式：equal_installment/equal_principal |
| `--area` | float | 否 | 90 | 房屋面积（平方米） |
| `--is-first-home` | bool | 否 | True | 是否首套房 |
| `--compare` | str | 否 | None | 对比方案JSON字符串 |
| `--output` | str | 否 | None | 输出文件路径 |
| `--selftest` | flag | 否 | False | 运行自检 |

### 3.2 执行步骤

1. **参数校验**：检查必填参数，验证数值范围
2. **获取LPR**：尝试从API获取最新LPR，失败则使用默认值
3. **计算贷款金额**：`贷款金额 = 房价 × (1 - 首付比例)`
4. **计算月供**：根据还款方式调用对应算法
5. **计算税费**：根据房屋属性计算各项税费
6. **评估现金流**：计算DTI并给出安全评级
7. **生成建议**：基于以上结果生成购房建议
8. **输出结果**：JSON格式输出或保存到文件

### 3.3 置信度门控

| 条件 | 置信度 | 处理方式 |
|------|--------|----------|
| LPR API 可用且返回有效数据 | 高 | 使用 API 数据，标注来源 |
| LPR API 不可用，使用默认值 | 中 | 使用默认值，明确提示"LPR为默认值，请以银行实际为准" |
| 输入参数超出合理范围（如房价>1亿） | 低 | 输出警告，建议人工复核 |

### 3.4 错误码

| 错误码 | 含义 | 处理方式 |
|--------|------|----------|
| E1001 | 房价必须为正数 | 提示用户重新输入 |
| E1002 | 收入必须为正数 | 提示用户重新输入 |
| E1003 | 首付比例必须在0-1之间 | 提示用户重新输入 |
| E1004 | 贷款年限必须在1-30年 | 提示用户重新输入 |
| E1005 | LPR不能为负数 | 提示用户重新输入 |
| E1006 | 基点必须在-100到200之间 | 提示用户重新输入 |
| E1007 | 还款方式非法 | 提示用户重新输入 |
| E2001 | LPR API请求失败 | 使用默认LPR并提示 |
| E2002 | 输出文件写入失败 | 提示用户检查路径 |
| E3001 | 内部计算错误 | 提示用户联系开发者 |

### 3.5 FAQ / 反模式

| 问题 | 正确做法 | 反模式 |
|------|----------|--------|
| 用户问"房价会涨吗" | 明确告知不预测房价 | 给出涨跌预测 |
| 用户问"银行会批多少贷款" | 告知以银行审批为准 | 承诺贷款额度 |
| 用户输入极端值（如房价0） | 返回错误码E1001 | 静默处理或输出NaN |
| 用户要求"随便算算" | 使用默认参数计算 | 拒绝服务 |
| LPR API超时 | 使用默认LPR并提示 | 无限等待或崩溃 |

## 四、输出格式

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
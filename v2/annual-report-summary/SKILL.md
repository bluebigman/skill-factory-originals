---
slug: annual-report-summary
name: annual-report-summary
displayName: 年报速读 财务透视 决策简报
description: 快速解析上市公司年报，提炼投资决策关键财务信息。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FinSight Studio
agent_created: true
trigger_words: ["年报解读", "财报分析", "年度报告摘要", "财务数据提炼", "投资决策支持"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 年报速读 · 财务透视 · 决策简报

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 编号 | 能力项 | 说明 | 输出示例 |
|------|--------|------|----------|
| C01 | 营收与利润趋势分析 | 提取近3-5年营业收入、净利润、扣非净利润，计算同比增速 | `营收 CAGR ≈ 12.3%（2021-2023）` |
| C02 | 盈利能力指标拆解 | 毛利率、净利率、ROE、ROIC 的数值与变化趋势 | `ROE 从 18.2% 降至 14.7%，主因净利率下滑` |
| C03 | 偿债能力与流动性体检 | 资产负债率、流动比率、速动比率、有息负债规模 | `资产负债率 58.3%，流动比率 1.32，短期偿债压力可控` |
| C04 | 经营现金流质量判断 | 经营性现金流净额、收现比、净现比 | `净现比 0.85，利润含金量偏低，需关注应收账款` |
| C05 | 费用结构与研发投入 | 销售/管理/财务费用率、研发费用率及同比变化 | `研发费用率 7.2%，同比提升 1.1pct，聚焦新业务线` |
| C06 | 关键财务风险信号识别 | 商誉占比、存货周转、应收账款周转、非标审计意见 | `商誉占净资产 32%，存在减值风险` |
| C07 | 业务分部与区域结构 | 分产品/分地区收入占比及增速 | `海外收入占比 41%，同比增长 23%` |

### 1.2 不能做什么

| 编号 | 限制项 | 说明 |
|------|--------|------|
| X01 | 不提供投资建议 | 不判断买入/卖出时机，不给出目标价 |
| X02 | 不预测未来业绩 | 不基于历史数据外推未来盈利 |
| X03 | 不替代完整审计 | 不验证年报数据真实性，仅做文本提炼 |
| X04 | 不处理非结构化附件 | 无法解析 PDF 中的扫描件、图片表格 |
| X05 | 不比较同行业公司 | 除非用户主动提供可比公司数据 |

### 1.3 适用对象

- 个人投资者：需要快速了解持仓或关注标的的财务健康度
- 财务分析师：作为初步筛选工具，定位需深挖的科目
- 财经记者：撰写年报快讯前的数据核对清单
- 企业战略人员：对标同行年报中的关键指标


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
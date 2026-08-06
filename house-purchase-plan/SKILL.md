---
slug: house-purchase-plan
name: house-purchase-plan
displayName: 购房测算 月供评估 预算规划
description: 输入收入与房价，输出月供、税费、现金流压力与购房建议。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 居安测算工坊
agent_created: true
trigger_words: ["house-purchase-plan", "买房测算", "月供计算", "购房预算", "房贷方案对比", "置业评估", "按揭压力测试"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

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

### 1.1 本 Skill 能做什么

| 序号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 月供估算 | 基于贷款金额、期限、利率（LPR+基点）计算等额本息/等额本金月供 |
| 2 | 税费概算 | 契税、个税、增值税、中介费、维修基金等常规费用估算 |
| 3 | 现金流压力评估 | 对比月供与家庭月收入，输出负债收入比（DTI）与安全边际 |
| 4 | 购房建议生成 | 根据首付比例、利率浮动、收入水平给出方向性建议 |
| 5 | 方案对比 | 支持多组参数并列输入，输出对比表格 |

### 1.2 本 Skill 不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不提供法律意见 | 涉及产权纠纷、合同条款解释请咨询律师 |
| 2 | 不做投资回报预测 | 不预测房价涨跌、租金收益率、资产增值 |
| 3 | 不替代银行审批 | 实际贷款额度、利率以银行最终审批为准 |
| 4 | 不覆盖所有城市政策 | 限购、限贷、公积金政策因城市而异，需人工核对 |
| 5 | 不处理非住宅类房产 | 商铺、写字楼、厂房等不在本工具范围内 |

### 1.3 适用对象

- 首次购房的工薪家庭
- 考虑换房的改善型买家
- 需要快速比较不同贷款方案的个人
- 房产中介或金融顾问的初步测算辅助


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

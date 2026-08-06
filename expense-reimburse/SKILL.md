---
slug: expense-reimburse
name: expense-reimburse
displayName: 报销单据 发票核验 明细归类
description: 整理报销单据，核验发票真伪，核对金额，归类并生成明细表。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 财务流程优化组
agent_created: true
trigger_words: ["报销", "发票", "单据整理", "费用归类", "报销单"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

> 本 Skill 由 AI 辅助生成，仅供参考，不构成任何专业财务建议。

# 报销单据整理与核验 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 序号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 单据整理 | 将散落的报销凭证（发票、收据、行程单等）按统一规则归类排序 |
| 2 | 发票真伪核验 | 对发票代码、号码、校验码进行逻辑校验（非官方查验） |
| 3 | 金额核对 | 比对单据金额与报销申请金额，标记差异 |
| 4 | 明细表生成 | 输出结构化报销明细表（Markdown/CSV格式） |
| 5 | 批量处理 | 支持多文件、多批次统一处理 |

### 1.2 不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不替代官方查验 | 无法连接税务系统，仅做格式与逻辑校验 |
| 2 | 不处理纸质原件 | 仅处理电子文件（PDF、JPG、PNG等） |
| 3 | 不提供法律意见 | 不判断发票是否涉及虚开、伪造等法律问题 |
| 4 | 不自动提交报销 | 不连接任何财务系统，仅生成整理结果 |

### 1.3 适用对象

- 需要整理月度/季度报销单据的职场人员
- 财务部门需要批量核对报销凭证的场景
- 个人需要归档整理发票的日常需求


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

---
slug: contract-review-check
name: contract-review-check
displayName: 合同审查 风险清单 条款核查
description: 对合同文本进行风险点审查，输出违约、付款、保密、知产归属的核查意见清单。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 法务工坊·条款勘验组
agent_created: true
trigger_words: ["contract-review-check", "合同审查", "风险清单", "条款核查", "合同体检", "合同风险扫描", "条款合规检查"]
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

# 合同审查风险清单核查 Skill 使用指南

## 一、能力边界（一页纸速查卡）

### 1.1 本 Skill 能做什么

| 能力项 | 说明 | 输出形式 |
|--------|------|----------|
| 违约条款审查 | 识别违约责任约定是否明确、对等、可执行 | 风险提示 + 条款原文摘录 |
| 付款条款审查 | 核查付款节点、金额、条件、发票、逾期利息等要素 | 风险提示 + 缺失项标注 |
| 保密条款审查 | 检查保密范围、期限、例外情形、违约责任 | 风险提示 + 合规性判断 |
| 知识产权归属审查 | 确认成果归属、许可范围、侵权责任承担 | 风险提示 + 归属判定 |
| 风险等级标注 | 对每项风险给出高/中/低三级标注 | 等级标签 + 简要理由 |

### 1.2 本 Skill 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不提供法律意见 | 输出仅为风险提示清单，不构成正式法律意见书 |
| 不替代律师审核 | 复杂交易或高标的合同须由执业律师把关 |
| 不处理非文本输入 | 仅支持文本格式合同，不支持扫描件 OCR 识别 |
| 不判断合同效力 | 不评估合同整体法律效力，仅做条款层面核查 |
| 不保证无遗漏 | 审查基于规则匹配，可能存在未覆盖的风险点 |

### 1.3 适用对象

- 企业法务、合规人员日常合同初审
- 商务人员签署前自查
- 合同模板标准化检查
- 合同归档前的规范性复核


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
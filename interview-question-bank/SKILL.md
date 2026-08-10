---
slug: interview-question-bank
name: interview-question-bank
displayName: 岗位JD解析 面试题库生成
description: 解析岗位JD，自动生成行为、专业、压力三类面试题及评分标准。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 知聘工坊
agent_created: true
trigger_words: ["面试题生成", "JD解析", "行为面试", "专业面试", "压力面试", "岗位画像", "招聘题库"]
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

# 岗位JD解析 · 面试题库生成 Skill

## 一、能力边界（一页纸速查卡）

| 维度 | 说明 |
|------|------|
| **核心能力** | 从岗位JD文本中提取关键任职要求，自动生成三类面试题（行为/专业/压力）及对应评分标准 |
| **输入要求** | 岗位JD文本（纯文本或Markdown格式），建议包含岗位职责、任职资格、加分项等字段 |
| **输出产物** | 结构化面试题库：每类题目3-5道，每题附评分维度、评分等级（1-5分）及参考观察点 |
| **可处理岗位类型** | 技术类、产品类、运营类、职能类、管理类等常见岗位 |
| **不可处理场景** | ① 无JD文本的岗位（需先补充描述）；② 非中文JD（需先翻译）；③ 需要视频/语音面试评估（超出文本分析范畴） |
| **适用对象** | 招聘HR、业务面试官、猎头顾问、招聘团队管理者 |

### 能力边界明细

**能做：**
- 解析JD中的硬性技能（如"精通Java"）与软性素质（如"抗压能力强"）
- 将JD要求映射到行为面试题（STAR法则）、专业面试题（技术/业务深度）、压力面试题（情境压力测试）
- 为每道题生成可量化的评分标准（含评分维度、行为锚点、常见误区）

**不能做：**
- 替代真实面试官进行主观判断
- 保证面试题与候选人实际表现之间的绝对相关性
- 生成超出JD文本信息范围的题目（如JD未提及的特定技术栈）


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
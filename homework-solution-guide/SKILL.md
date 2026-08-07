---
slug: homework-solution-guide
name: homework-solution-guide
displayName: 作业引导 思路启发 自主解题
description: 用提问代替讲解，引导中小学生自主解出作业题。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 启思教练
agent_created: true
trigger_words: ["作业帮", "讲题", "这题怎么做", "解题思路", "辅导作业", "教我一下", "帮我想想", "下一步咋办"]
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

# 作业引导 · 思路启发 · 自主解题（SKILL.md）

## 一、能力边界（一页纸速查卡）

### 1.1 本 Skill 能做什么

| 能力项 | 说明 | 适用场景 |
|--------|------|----------|
| 题目拆解 | 将一道题拆成若干可独立思考的小步骤 | 学生说"看不懂题"、"没思路" |
| 思路引导 | 用提问代替直接讲解，逐步启发学生自己找到解法 | 学生卡在中间步骤、思路跑偏 |
| 知识点回顾 | 用学生能理解的语言复述核心公式/概念/语法点 | 学生基础概念模糊、公式记混 |
| 错题归因 | 结合错题本记录，分析错误类型并给出针对性变式练习 | 同一类型题反复出错 |
| 下一步建议 | 推荐同类练习、复习内容或变式任务 | 学生做完一题后不知道练什么 |

### 1.2 本 Skill 不能做什么

| 禁止事项 | 原因 | 替代方案 |
|----------|------|----------|
| 直接给出答案 | 违背"自主解题"核心目标 | 提供提示性问题，引导学生自己算出结果 |
| 替代老师批改作业 | 本 Skill 不判断对错，只引导思路 | 建议学生对照课本答案或请教老师 |
| 处理超纲内容（如大学高等数学） | 设计面向中小学（K9-K12） | 建议使用其他专业工具 |
| 保证提分效果 | 学习效果受多因素影响 | 只提供方法，不承诺结果 |

### 1.3 适用对象

- 小学三年级至高中三年级学生（7-18岁）
- 家长（辅导孩子作业时使用）
- 自学学生（遇到难题时自我引导）


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
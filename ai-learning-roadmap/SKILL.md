---
slug: ai-learning-roadmap
name: ai-learning-roadmap
displayName: AI学习路径 分周规划 资源验收
description: 根据基础与目标，生成含资源与验收的AI分周学习路线。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["ai-learning-roadmap", "AI学习路线", "AI学习计划", "分周学习", "AI课程规划", "机器学习路径"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# AI 学习路线规划器（AI Learning Roadmap）

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入处理 | 识别用户基础水平（关键词匹配）、学习目标、时间约束 | 无法进行代码级能力测评或笔试 |
| 路线生成 | 生成 4-16 周的分周学习计划，含主题、资源、实战、验收 | 无法生成实时更新的课程链接（资源库固定） |
| 资源推荐 | 从内置资源库（Microsoft AI-For-Beginners 等）选取章节 | 无法推荐付费课程或需授权的内容 |
| 质量保障 | 内部评分（0-100），低于 80 自动调整重生成 | 无法保证学习效果，不承诺就业或能力飞跃 |
| 输出格式 | 标准 Markdown 文档，结构化字段 | 无法输出 PDF、PPT 等非 Markdown 格式 |

### 1.2 适用对象

- **新手入门**：零基础或仅了解基本编程概念，想系统学习 AI 但不知从何下手
- **转行学习者**：有编程经验但未接触过机器学习/深度学习，需要结构化路径
- **进阶提升者**：已有一定基础，希望针对特定方向（如 NLP、CV）深入

### 1.3 不适用场景

- 需要实时课程价格、开课时间等动态信息
- 需要一对一导师互动或作业批改服务
- 需要针对特定企业技术栈的定制化培训方案

---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

## 二、触发方式

### 2.1 触发词速查

| 触发词 | 场景示例 |
|--------|----------|
| `ai-learning-roadmap` | 直接调用 Skill 名称触发 |
| `AI学习路线` | "帮我生成一个 AI 学习路线" |
| `AI学习计划` | "我想制定一个 AI 学习计划" |
| `分周学习` | "给我一个分周的学习安排" |
| `机器学习路径` | "机器学习应该按什么路径学？" |

### 2.2 大白话场景映射

| 用户说 | 系统理解 |
|--------|----------|
| "我啥都不会，想学 AI" | 基础=零基础，目标=全面入门 |
| "我会 Python，想搞机器学习" | 基础=有编程经验，目标=机器学习专项 |
| "我学过深度学习，想搞 NLP" | 基础=中级，目标=NLP 方向 |
| "只有 4 周时间，能学啥？" | 时间约束=4 周，生成紧凑路线 |


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
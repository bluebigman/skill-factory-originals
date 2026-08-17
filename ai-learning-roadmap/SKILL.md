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
author: SkillForge Studio
agent_created: true
trigger_words: ["ai-learning-roadmap", "AI学习路线", "AI学习计划", "分周学习", "AI课程规划", "AI学习路径", "AI技能树", "AI进阶路线"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# AI 学习路线规划 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 |
|--------|------|
| 生成分周学习计划 | 根据用户的基础水平与学习目标，输出 4~16 周的结构化学习路线 |
| 推荐学习资源 | 为每个学习阶段推荐对应的课程、文档、开源项目或练习素材 |
| 设定验收标准 | 为每个阶段定义可检查的产出物（如小项目、测验通过、代码仓库） |
| 动态调整建议 | 当用户反馈进度偏差时，提供调整策略（如压缩/扩展某阶段） |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不提供实时课程链接 | 资源以名称+来源平台形式给出，不保证链接永久有效 |
| 不评估用户真实水平 | 仅依据用户自述的基础信息进行规划，不进行在线测评 |
| 不承诺学习效果 | 不保证完成路线后必然达到某种职业能力或薪资水平 |
| 不替代导师答疑 | 遇到具体技术问题，需自行查阅文档或求助社区 |

### 1.3 适用对象

- 想系统学习 AI 但不知从何入手的初学者
- 已有编程基础、希望转向 AI 方向的开发者
- 需要为团队制定 AI 技能提升计划的负责人

---

## 二、触发方式

### 2.1 触发词

直接使用以下任一说法即可触发本 Skill：

- "帮我规划 AI 学习路线"
- "生成一份分周学习计划"
- "我想学 AI，怎么安排？"
- "AI 课程规划"
- "AI 学习路径"

### 2.2 场景映射表

| 用户说（大白话） | 本 Skill 理解 |
|------------------|---------------|
| "我啥都不会，想学 AI" | 基础=零基础，目标=入门 AI 通识 |
| "我会 Python，想搞机器学习" | 基础=有编程经验，目标=机器学习专项 |
| "我想做 AI 产品经理" | 基础=非技术背景，目标=AI 应用与产品思维 |
| "我只有 4 周时间，想快速了解" | 时间约束=4周，目标=概览型学习 |

---

## 三、标准流程

### 3.1 前置条件

在生成路线前，需要确认以下输入信息（至少 3 项）：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `base_level` | string | 是 | 无 | 可选值：`zero`（零基础）、`programmer`（有编程经验）、`practitioner`（有 AI 基础） |
| `goal` | string | 是 | 无 | 学习目标描述，如"入门机器学习"、"掌握深度学习"、"AI 产品设计" |
| `weeks` | int | 否 | 8 | 学习周期（4~16 周） |
| `hours_per_week` | int | 否 | 10 | 每周可投入学习小时数（5~40） |
| `preferred_style` | string | 否 | `mixed` | 可选值：`video`（视频为主）、`reading`（文档为主）、`project`（项目驱动）、`mixed`（混合） |

### 3.2 执行步骤

1. **收集输入**：通过对话或命令行参数获取上述参数。若信息不足，使用 [需核实:字段名] 占位，并提示用户补充。
2. **确定学习阶段**：根据 `base_level` 和 `goal` 将学习周期划分为 3~5 个阶段（如：基础铺垫 → 核心概念 → 实践应用 → 项目实战 → 进阶探索）。
3. **分配周次**：将总周数按阶段权重分配（权重参考：基础 20%、核心 30%、实践 25%、项目 20%、进阶 5%）。
4. **填充资源与验收**：为每个阶段匹配资源类型（课程/文档/项目）和验收标准（产出物/测验/代码）。
5. **输出结构化结果**：按下方"输出规范"格式呈现。

### 3.3 输出规范

输出必须包含以下结构：

```
# AI 学习路线（{weeks} 周）

## 学习画像
- 基础水平：{base_level}
- 学习目标：{goal}
- 每周投入：{hours_per_week} 小时

## 阶段总览
| 阶段 | 周次 | 主题 | 验收标准 |
|------|------|------|----------|
| ...  | ...  | ...  | ...      |

## 详细计划
### 第 1 周：{主题}
- **学习内容**：...
- **推荐资源**：...
- **练习任务**：...
- **验收标准**：...

（后续周次依此类推）

## 调整建议
- 若进度超前：...
- 若进度落后：...
```

---

## 四、置信度门控

当以下信息缺失时，不得编造内容，必须输出 `[需核实:字段名]` 占位：

| 缺失字段 | 输出示例 |
|----------|----------|
| `base_level` | "请先告诉我您的基础水平（零基础/有编程经验/有AI基础），以便生成合适的路线。" |
| `goal` | "请描述您的学习目标，例如'入门机器学习'或'掌握深度学习'。" |
| `weeks` | "请指定学习周期（4~16周），否则默认按 8 周规划。" |
| 具体资源名称 | "该阶段推荐资源：[需核实:具体课程名称]，建议搜索'机器学习 入门 课程'获取最新推荐。" |

---

## 五、错误码体系

| 错误码 | 触发场景 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `E001` | 未提供 `base_level` | "缺少基础水平信息，无法确定起点。" | 请用户选择：零基础 / 有编程经验 / 有AI基础 |
| `E002` | 未提供 `goal` | "缺少学习目标，无法规划方向。" | 请用户描述目标，或从预设目标中选择 |
| `E003` | `weeks` 超出 4~16 范围 | "学习周期需在 4~16 周之间。" | 自动截断到边界值，并提示用户 |
| `E004` | `hours_per_week` 超出 5~40 范围 | "每周投入时间需在 5~40 小时之间。" | 自动截断到边界值，并提示用户 |
| `E005` | 资源推荐失败 | "当前阶段资源暂无法匹配，请稍后重试或调整偏好。" | 使用通用资源关键词替代，并标注 [需核实] |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式（错误做法） | 正模式（正确做法） |
|----|--------------------|--------------------|
| 盲目堆资源 | 一次性列出 20 个课程链接 | 按阶段只推荐 2~3 个核心资源 |
| 忽略验收 | 只列学习内容，无检查点 | 每周设置明确产出物（代码/笔记/测验） |
| 不切实际 | 零基础 4 周学完深度学习 | 根据基础水平合理分配阶段权重 |
| 静态规划 | 生成后不再调整 | 提供进度反馈后的调整策略 |

### 6.2 反模式对照表

| 用户需求 | 反模式响应 | 正模式响应 |
|----------|------------|------------|
| "我要 2 周速成 AI" | "好的，2 周安排如下..." | "2 周时间较短，建议聚焦 AI 通识概览，完整掌握需 8 周以上。是否调整目标？" |
| "推荐最好的课程" | "XX 课程是最好的" | "根据您的偏好，推荐以下 2 个备选课程，您可根据风格选择。" |
| "学完能进大厂吗" | "学完保证进大厂" | "学习路线可帮助建立知识体系，就业结果受多种因素影响，无法承诺。" |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

1. 告诉 AI 你的基础（零基础/有编程经验/有AI基础）
2. 告诉 AI 你的目标（如"入门机器学习"）
3. 告诉 AI 你有几周时间（4~16 周）
4. 获取分周计划，按周执行并完成验收

### 7.2 新手阅读路径

- 先看「能力边界」了解工具限制
- 直接使用「触发方式」中的说法发起请求
- 按「输出规范」检查生成结果是否完整

### 7.3 进阶阅读路径

- 深入理解「置信度门控」机制，主动补充信息以获得更精准规划
- 参考「错误码体系」排查生成失败原因
- 利用「FAQ 反模式」优化自己的学习预期

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应自行承担使用本 Skill 产生的全部责任。本 Skill 提供的学习规划仅供参考，不构成任何形式的教学承诺或就业保证。
2. **禁止反向工程**：使用者不得对本 Skill 的提示词、内部逻辑进行反向工程、破解、提取或用于商业竞争。
3. **内容变更**：本 Skill 可能随时更新，恕不另行通知。使用者应关注最新版本。
4. **合规使用**：使用者不得将本 Skill 用于任何违反法律法规或侵犯第三方权益的用途。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 SkillForge Studio

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

---
slug: ai-learning-roadmap
name: ai-learning-roadmap
displayName: AI自学路径 分周规划 课程推荐
description: 根据基础与目标，生成含资源与验收的AI分周学习路线。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ai-learning-roadmap
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge
agent_created: true
trigger_words: 
  - "ai-learning-roadmap"
  - "AI学习计划"
  - "AI路线图"
  - "AI课程规划"
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# AI 学习路线图生成器

## 一、前置条件

### 1.1 用户输入要求
在调用本 Skill 前，请确认已收集到以下**至少两项**信息：

| 信息项 | 说明 | 示例 |
|--------|------|------|
| **基础水平** | 零基础 / 初级（懂Python）/ 中级（懂ML基础）/ 高级（可独立建模） | "我会Python，但没做过机器学习" |
| **学习目标** | 入门AI / 机器学习 / 生成式AI / 实战项目 | "我想搞懂大模型原理" |
| **可选参数** | 周数（4/8/12/16）、每日时长（1/2/3小时）、资源偏好（视频/文档/代码） | "每周10小时，偏好视频课" |

若上述信息缺失，本 Skill 将输出**带置信度提示**的路线图，并主动追问缺失项。

### 1.2 资源库说明
本 Skill 默认引用以下公开高质量资源（均为免费或部分免费）：

- **微软 AI 课程**：`https://github.com/microsoft/ai-for-beginners`
- **吴恩达《机器学习》专项课程**：`https://www.coursera.org/specializations/machine-learning-introduction`
- **Fast.ai 实战课程**：`https://course.fast.ai/`
- **Hugging Face 课程**：`https://huggingface.co/learn/nlp-course`

> 注意：以上链接内容可能更新，请以实际页面为准。本 Skill 只做推荐，不保证课程永久免费。

---

## 二、执行步骤

### 步骤 1：解析用户输入

1. **识别基础水平**（关键词匹配）：
   - 零基础：无编程经验 / 刚学Python / 不懂ML
   - 初级：会Python语法 / 用过NumPy / 未系统学过ML
   - 中级：懂线性回归 / 用过sklearn / 了解过拟合
   - 高级：能独立完成Kaggle入门赛 / 懂深度学习框架

2. **识别学习目标**：
   - 入门AI → 侧重概念与工具链
   - 机器学习 → 侧重算法原理与实现
   - 生成式AI → 侧重Transformer、扩散模型、微调
   - 实战项目 → 侧重端到端项目流程

3. **识别可选参数**：
   - 若用户未指定周数，按基础水平分配默认值（见步骤2）
   - 若用户未指定每日时长，默认 1.5 小时/天

### 步骤 2：生成分周计划（核心逻辑）

按下表确定**周数**与**内容深度**：

| 基础水平 | 默认周数 | 内容深度描述 |
|----------|----------|--------------|
| 零基础   | 12 周    | 前4周补Python基础，中间4周学ML入门，最后4周做简单项目 |
| 初级     | 8 周     | 前2周快速复习，中间4周学核心ML算法，最后2周实战 |
| 中级     | 8 周     | 前2周深度学习基础，中间4周学神经网络，最后2周微调 |
| 高级     | 4 周     | 直接进入生成式AI/前沿模型，每周一个专题 |

**每周结构固定为 4 个模块：**
1. **本周主题**（一句话概括）
2. **学习资源**（从资源库中选取，注明章节或视频编号）
3. **实战练习**（小作业或代码实验，附验收标准）
4. **验收标准**（可量化的检查点，如"能独立完成XX"）

### 步骤 3：处理不确定项与常见误区

- **置信度标注**：当用户输入模糊时，在路线图头部标注 `置信度：70%`，并注明"基础水平为推测值，建议确认"。
- **误区纠正**：若用户要求"零基础直接学Transformer"，在路线图中插入警示框，建议先完成前几周基础。

### 步骤 4：输出与自检

1. 组装 Markdown 文档，结构见下一节。
2. 内部质量评分（0-100）：
   - 资源匹配度（所选课程是否贴合目标）：权重 40%
   - 时间合理性（周数×每日时长是否超负荷）：权重 30%
   - 难度递进性（每周是否有衔接）：权重 30%
3. 若评分 < 80，自动调整周数或资源，重新生成。

---

## 三、输出格式

生成结果必须包含以下章节（Markdown 格式）：

```markdown
# AI 学习路线图（[基础水平] → [学习目标]）

> 置信度：XX% （若有不明确项）
> 生成日期：YYYY-MM-DD

## 总览
| 周数 | 总学习时长 | 核心主题 |
|------|------------|----------|
| 第1-2周 | X小时 | ... |

## 详细计划

### 第 1 周：〔主题〕
- **学习资源**：课程名 + 链接 + 具体章节
- **实战练习**：描述任务
- **验收标准**：你能做到什么？

### 第 2 周：……
（直至最后一周）

## 三条建议
1. 针对你的[基础/目标]，建议……
2. 常见误区提醒：……
3. 推荐补充资源：……

## 失败处理
若本计划不适合你，请重新提供基础水平或目标关键词。
```

---

## 四、失败处理

| 场景 | 处理方式 |
|------|----------|
| 用户输入为空白或乱码 | 返回错误提示，并给出正确示例："请按'基础水平 + 目标 + 可选参数'格式描述，例如：零基础，想入门AI，8周，每天2小时" |
| 用户要求超出能力范围（如"4周成为专家"） | 拒绝生成，并说明合理周数范围 |
| 用户输入矛盾（如"零基础但会Transformer"） | 以"基础水平"为准，在置信度中标注矛盾，并追问确认 |
| 推荐资源链接失效 | 在输出中标注"资源可能已更新"，同时提供备选资源（如替代课程） |
| 用户中途修改参数 | 重新执行步骤1-4，并在新输出中注明"已根据新参数重新生成" |

---

## 五、示例输出片段（供参考）

### 第 3 周：Python 数据分析基础（零基础路线）

- **学习资源**：微软 AI for Beginners 课程，第 2 章（Python 与 NumPy），视频约 45 分钟
- **实战练习**：用 NumPy 完成矩阵乘法，并计算一个小数据集的均值/方差
- **验收标准**：能在 30 分钟内独立写出上述代码，无语法错误

---

## 附：自检清单

生成完毕后，请确认：

- [ ] 包含"前置条件"所需信息
- [ ] 每周均有资源、练习、验收三要素
- [ ] 置信度标注清晰
- [ ] 未使用绝对化用语（如"保证"）
- [ ] 未承诺任何收益或就业

若以上任一未通过，请修正后重新输出。

## 许可证（License）

```text
MIT License

Copyright (c) 2026 SkillForge Lab

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```
<!-- professional-license-embedded -->

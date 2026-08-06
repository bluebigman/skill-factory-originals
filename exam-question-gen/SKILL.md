---
slug: exam-question-gen
name: exam-question-gen
displayName: 智能出题 知识点覆盖 题型难度配置
description: 按知识点、题型与难度自动生成配套解析的练习题。
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
trigger_words: ["出题", "生成题目", "组卷", "测验生成", "练习题", "习题生成", "试卷生成"]
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

# 智能出题 Skill 使用指南

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 按知识点出题 | 指定具体知识点，生成对应题目 | "出题，知识点：勾股定理" |
| 题型指定 | 选择题、填空题、解答题、判断题 | "用选择题出题" |
| 难度配置 | 简单/中等/困难，或自定义比例 | "难度比例 3:5:2" |
| 数量控制 | 指定题目数量，默认 5 道 | "出 8 道题" |
| 批量生成 | 多知识点、多题型组合出题 | "知识点[功,功率]，题型[选择,解答]" |
| 结构化输出 | 支持 Markdown 或 JSON 格式 | "以 JSON 格式输出" |
| 组卷建议 | 附带分值分配与时间规划 | "并给出试卷结构建议" |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 无知识点输入 | 若未提供知识点，将使用通用基础知识点（如"数学基础运算"） |
| 不保证教学效果 | 题目仅用于练习，不替代系统教学 |
| 不生成超纲内容 | 难度上限为"困难"，不涉及竞赛级或超纲题目 |
| 不提供答案详解 | 仅提供正确答案，不生成解题思路（除非额外要求） |

### 1.3 适用对象

- 教师：快速生成课堂练习或课后作业
- 学生：自主练习，巩固知识点
- 培训机构：批量生成测验试卷
- 教育产品开发者：程序化调用生成题目数据


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ai-learning-roadmap
name: ai-learning-roadmap
displayName: AI学习路径规划 分周路线图 技能进阶
description: 根据用户基础与目标，从微软AI课程等资源生成分周学习计划与路线图。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ai-learning-roadmap
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["ai-learning-roadmap", "AI学习路线图", "生成式AI学习计划", "AI学习路径", "分周学习计划", "微软AI课程"]

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

# AI 学习路线图生成器（Skill 文档）

## 一、能力边界：一页纸速查卡

### 1.1 本 Skill 能做什么

| 序号 | 核心能力 | 说明 |
|------|----------|------|
| 1 | 解析用户输入 | 从自然语言描述中提取「当前基础水平」「学习目标」「可用时间」三个关键参数 |
| 2 | 匹配高质量资源 | 默认优先匹配微软 AI 课程体系（如 AI-900、AI-102、生成式 AI 系列），也可接受用户指定的其他资源 URL |
| 3 | 生成分周计划 | 按周拆分学习任务，每周围绕一个主题模块，包含学习材料、动手练习、自测题 |
| 4 | 输出 Markdown 路线图 | 生成结构化的 Markdown 文档，含周次、主题、资源链接、里程碑检查点 |
| 5 | 置信度标注 | 对推断出的用户基础、目标匹配度、资源适用性给出置信度提示 |

### 1.2 本 Skill 不能做什么

| 序号 | 限制说明 |
|------|----------|
| 1 | 不提供实时课程内容或视频播放链接（仅提供课程页面 URL） |
| 2 | 不保证学习效果或就业结果（学习效果取决于个人投入） |
| 3 | 不替代专业导师的一对一指导 |
| 4 | 不生成代码或项目源码（仅规划学习路径） |
| 5 | 不处理非 AI 领域的学习规划请求 |

### 1.3 适用对象

- **零基础入门者**：想了解 AI 是什么，希望从概念开始建立认知框架
- **在职转行者**：具备编程基础，希望系统学习机器学习或深度学习
- **应用实践者**：已了解 AI 基础，希望聚焦生成式 AI、大模型应用开发
- **项目驱动学习者**：有具体项目想法，需要按项目需求倒推学习内容


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

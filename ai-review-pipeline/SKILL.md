---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ai-review-pipeline
name: ai-review-pipeline
displayName: 代码审查 自动化修复 报告生成
description: 一键执行代码审查、自动修复、测试生成与HTML报告输出。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ai-review-pipeline
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: CodePilot Studio
agent_created: true
trigger_words: ["ai-review-pipeline", "代码审查流水线", "自动修复代码", "审查报告生成", "code review pipeline"]

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

# AI 代码审查流水线（ai-review-pipeline）使用指南

## 一、能力边界：一页纸速查卡

本 Skill 提供一条完整的代码审查自动化链路：从输入代码仓库或文件集，到输出结构化审查报告、自动修复补丁、测试用例建议，最终生成一份可离线浏览的 HTML 报告。

### ✅ 能做什么（核心能力）

| 序号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 代码审查 | 对指定目录/文件进行静态扫描，识别潜在缺陷、风格问题、安全隐患 |
| 2 | 自动修复 | 对可确定性修复的问题（如格式、未使用变量）生成补丁并可选应用 |
| 3 | 测试生成 | 为关键函数/模块生成单元测试骨架（基于 pytest / JUnit 风格） |
| 4 | HTML 报告 | 将审查结果、修复状态、测试建议汇总为单文件 HTML 报告 |
| 5 | 多 AI 提供商适配 | 内置 6 种 AI 提供商接口（OpenAI / Anthropic / Gemini / 本地模型等），可切换后端 |

### ❌ 不能做什么（边界声明）

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行动态分析 | 不运行程序、不追踪运行时错误，仅做静态文本分析 |
| 2 | 不保证修复正确性 | 自动修复仅针对模式化问题，复杂逻辑缺陷需人工复核 |
| 3 | 不处理二进制文件 | 仅支持文本类源码文件（.py/.js/.java/.go/.rs/.ts 等） |
| 4 | 不替代人工审查 | 输出为辅助建议，最终决策权在开发者 |
| 5 | 不支持跨语言混合分析 | 单次运行针对一种主语言（通过扩展名过滤） |

### 适用对象

- 个人开发者：提交代码前快速自检
- 小型团队：无 CI 环境时的轻量审查替代方案
- 教育场景：向学生展示常见代码缺陷模式


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

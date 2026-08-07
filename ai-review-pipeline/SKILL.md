---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ai-review-pipeline
name: ai-review-pipeline
displayName: 代码审查 自动修复 报告生成
description: 一键执行代码审查、自动修复、测试生成与HTML报告输出。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ai-review-pipeline
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Studio
agent_created: true
trigger_words: ["代码审查", "code review", "审查", "review", "代码检查", "自动修复"]
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

# ai-review-pipeline — 代码审查流水线

## 一、能力边界（一页纸速查卡）

### 能做（核心能力）

| 序号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| 1 | 代码审查 | 对用户提供的代码文件或代码片段进行静态审查，识别潜在缺陷、安全隐患、性能瓶颈 | `review src/main.py` |
| 2 | 自动修复 | 针对可自动修复的问题（如格式、未使用变量、简单逻辑错误）生成补丁或直接修改 | `review --fix src/main.py` |
| 3 | 测试生成 | 根据代码逻辑自动生成单元测试用例（覆盖正常路径、边界条件、异常分支） | `review --test src/utils.py` |
| 4 | HTML 报告 | 将审查结果、修复建议、测试结果汇总为独立的 HTML 报告文件 | `review --report out/report.html` |
| 5 | 批量处理 | 支持一次审查多个文件或整个目录，输出汇总结果 | `review src/ tests/` |

### 不能做（明确边界）

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行代码 | 本工具只做静态分析，不运行目标代码，无法发现运行时才暴露的问题 |
| 2 | 不保证修复正确性 | 自动修复基于规则匹配，复杂逻辑错误需人工确认 |
| 3 | 不替代人工评审 | 生成的报告仅作参考，最终决策由开发人员负责 |
| 4 | 不支持所有语言 | 当前版本支持 Python、JavaScript、TypeScript、Go、Rust 的常见语法，其他语言可能解析失败 |
| 5 | 不处理二进制文件 | 仅接受文本格式的源代码文件 |

### 适用对象

- 个人开发者：提交代码前的快速自检
- 小型团队：代码合并前的初步审查
- 教学场景：帮助学生发现代码中的常见问题


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

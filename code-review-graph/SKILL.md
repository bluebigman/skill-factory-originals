---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: code-review-graph
name: code-review-graph
displayName: 代码审查 影响分析 图谱推演
description: 基于语法树构建调用图谱，精准定位代码变更影响边界。
version: 1.0.8
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/code-review-graph
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 图谱工坊
agent_created: true
trigger_words: ["code-review-graph", "代码影响分析", "变更范围评估", "调用关系图谱", "diff影响面"]

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

# code-review-graph — 代码变更影响面分析 Skill

## 一、能力边界速查卡

### 1.1 能做什么

| 能力项 | 说明 | 典型场景 |
|--------|------|----------|
| 解析变更清单 | 接受 git diff、文件列表、commit 范围作为输入 | 提交 PR 前自查 |
| 构建调用图谱 | 基于 Tree-sitter 提取函数、类、模块间的静态调用关系 | 理解模块耦合度 |
| 影响范围计算 | 从变更点出发，沿图谱反向追踪所有可能受影响的调用方 | 评估重构风险 |
| 批量合并分析 | 多文件、多 commit 的变更去重后统一计算 | 合并主干前的综合评估 |
| 多格式输出 | JSON / Markdown / CSV / SVG 可视化 | 对接 CI 或人工阅读 |
| 增量构建 | 仅重建变更文件的 AST 子图，其余走缓存 | 大型仓库的日常增量审查 |
| 降级保障 | 图谱构建失败时自动回退到文本 diff 分析 | 语法错误或极端文件 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行动态分析 | 不运行测试、不追踪运行时调用链 |
| 不保证语义正确 | 静态分析结果仅代表语法层面的调用关系，不判断逻辑对错 |
| 不处理跨语言调用 | 仅支持单语言项目的图谱构建（可通过 `--lang` 指定） |
| 不覆盖全部边界场景 | 动态调用、宏展开等场景依赖启发式策略，存在误判可能 |
| 不替代人工审查 | 输出的是影响面候选清单，最终判断需人工确认 |

### 1.3 适用对象

- 需要评估重构风险的开发者
- 需要做 Code Review 前置筛选的团队
- 需要理解模块依赖关系的新人 onboarding
- CI 流水线中需要自动生成影响报告的运维/QA


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

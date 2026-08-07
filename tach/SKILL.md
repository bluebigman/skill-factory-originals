---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: tach
name: tach
displayName: 依赖透视 架构边界 一致性校验
description: 解析项目依赖关系，可视化架构边界并执行一致性校验。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/tach
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["tach", "依赖可视化", "架构边界", "依赖检查", "模块约束", "依赖关系", "架构守护", "模块边界"]
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

# tach — 依赖透视与架构边界守护

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 典型场景 |
|--------|------|----------|
| 依赖解析 | 扫描项目源码，提取模块/包之间的引用关系 | 新接手代码库，想快速摸清模块间耦合 |
| 架构边界可视化 | 将依赖关系渲染为图形或结构化清单 | 向团队展示当前架构形态 |
| 一致性校验 | 对照预设的架构规则，检查实际依赖是否越界 | CI 流水线中拦截非法依赖 |
| 约束定义 | 声明允许/禁止的依赖方向与层级 | 推行分层架构（如 controller → service → dao） |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不分析运行时行为 | 仅静态扫描源码引用，不追踪反射、动态加载、运行时注册 |
| 不识别语义耦合 | 不判断两个模块是否因业务逻辑而隐式关联 |
| 不自动修复违规 | 只报告违规点，不提供自动重构或代码改写 |
| 不支持所有语言 | 需确认目标语言是否在支持列表内（见 1.3） |

### 1.3 适用对象

- **适用**：Python、TypeScript/JavaScript 项目（主流支持）；Java/Kotlin 需确认插件可用性。
- **不适用**：C/C++ 宏定义依赖、Ruby 元编程动态依赖、未编译的 Scala 代码。
- **前置条件**：项目需有明确的包/模块目录结构；源码可被静态解析（无加密、无生成代码干扰）。


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

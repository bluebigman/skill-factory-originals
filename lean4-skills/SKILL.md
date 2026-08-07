---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: lean4-skills
name: lean4-skills
displayName: 定理证明 Lean4 形式化验证
description: Lean 4 定理证明辅助技能包，支持形式化验证与策略推导。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/lean4-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FormalForge Studio
agent_created: true
trigger_words: ["lean4-skills", "Lean 4", "定理证明", "形式化验证", "战术推导", "proof assistant"]
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

# Lean 4 定理证明技能包（SKILL.md）

## 1. 能力边界：一页纸速查卡

### 1.1 能做（核心能力清单）

| 编号 | 能力项 | 说明 | 输出形态 |
|------|--------|------|----------|
| C1 | 策略推导 | 根据目标定理，推荐 Lean 4 战术序列（如 `intro`、`apply`、`exact`、`rw`） | 战术步骤列表 |
| C2 | 错误诊断 | 解析 Lean 4 报错信息，定位语法/类型/作用域问题 | 错误码 + 修正建议 |
| C3 | 代码补全 | 对不完整的定理证明片段，补全缺失的战术或中间引理 | 可编译的 Lean 代码块 |
| C4 | 策略教学 | 对指定战术（如 `rcases`、`induction`）给出使用场景与示例 | 讲解 + 最小示例 |
| C5 | 项目结构梳理 | 分析 Lean 4 项目（`.lean` 文件、`lakefile.toml`），给出依赖与构建建议 | 结构化报告 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| N1 | 不执行 Lean 编译器 | 本技能不调用 `lean` 或 `lake` 命令，不进行实际编译验证 |
| N2 | 不保证证明正确性 | 生成的战术序列需用户在本地环境验证，不承担正确性担保 |
| N3 | 不处理非 Lean 语言 | 仅针对 Lean 4 语法，不解析 Coq、Agda、Isabelle 等其它证明助手 |
| N4 | 不访问外部数学库 | 不自动查询 Mathlib 最新 API，仅基于内置知识库（截至 2025 年初） |
| N5 | 不生成完整项目骨架 | 不创建 `lakefile.toml`、`Main.lean` 等工程文件，仅提供文本建议 |

### 1.3 适用对象

- **AI 编码代理**：需要嵌入 Lean 4 证明能力的自动化工作流。
- **Lean 初学者**：希望理解战术用法、快速定位语法错误。
- **形式化验证工程师**：需要战术推荐或代码片段补全。


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

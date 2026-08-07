---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: thundernet-review
name: thundernet-review
displayName: 代码审查 缺陷扫描 质量门禁
description: 将代码或文件输入转化为结构化审查报告，标注风险置信度。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/thundernet-review
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: linus-toolsmith
agent_created: true
trigger_words: ["代码审查", "code review", "缺陷扫描", "质量门禁", "静态分析", "thundernet-review"]
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

# ThunderNet Review — 代码审查与缺陷扫描 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做（核心能力清单）

| 编号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| C1 | 代码/文本结构化解析 | 将用户粘贴的代码片段、文件路径或 URL 指向的源码，解析为可审查的单元（函数、类、模块） | `def foo(): ...` 或 `/src/main.py` |
| C2 | 关键信息识别与保留 | 自动提取函数名、变量名、依赖调用、异常处理分支等关键要素，不丢失上下文 | 识别 `try/except` 块及其覆盖范围 |
| C3 | 约定格式输出 | 按固定模板生成 Markdown 审查报告，包含缺陷等级、位置、建议修复方案 | 输出 `### 缺陷 #1 [高]` 格式 |
| C4 | 置信度标注 | 对每一条审查结论给出 0-1 的置信度分数；信息不足时输出 `[需核实:字段名]` 占位符 | `置信度: 0.87` |
| C5 | 批量处理与自定义格式 | 支持一次提交多个文件（用 `---` 分隔），或通过参数指定输出格式（`--format json`） | 多文件批量审查 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| N1 | 不执行代码 | 本 Skill 仅做静态文本分析，不运行程序、不验证运行时行为 |
| N2 | 不替代人工评审 | 审查结果仅为辅助建议，最终决策需由具备资质的工程师确认 |
| N3 | 不处理二进制文件 | 仅支持文本类源码（.py/.js/.java/.go/.c/.cpp/.ts 等），不支持 .exe/.so/.class |
| N4 | 不保证发现全部缺陷 | 受限于输入完整度与上下文，可能遗漏跨文件或依赖外部服务的逻辑问题 |
| N5 | 不提供安全漏洞利用验证 | 对疑似安全风险仅做静态标记，不进行渗透测试或 PoC 构造 |

### 1.3 适用对象

- **适用**：个人开发者、小型团队、代码评审会议前的预检、CI 流水线中的静态扫描环节
- **不适用**：大型企业级合规审计、需要动态分析的性能调优、涉及商业秘密的敏感代码审查


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

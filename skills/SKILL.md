---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: skills
name: skills
displayName: 技能转换 规则解析 代码助手
description: 将Cursor规则转换为Claude Code技能，覆盖主流框架与语言。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge
agent_created: true
trigger_words: ["skills", "cursor rules", "claude code skills", "技能转换", "规则转换", "框架指南"]
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

# SKILL.md — 技能转换与规则解析助手

## 一、能力边界（一页纸速查卡）

### 能做（核心能力清单）

| 编号 | 能力项 | 说明 | 适用场景示例 |
|------|--------|------|--------------|
| 1 | 数据/文件/URL 结构化转换 | 将用户提供的原始材料解析为结构化结果 | 将 `.mdc` 规则文件转为 `SKILL.md` 格式 |
| 2 | 关键信息识别与保留 | 自动提取输入中的核心规则、参数、约束条件 | 从 Cursor 规则中提取触发词与行为规范 |
| 3 | 按约定格式生成输出 | 严格遵循目标格式（如 Markdown 结构）输出 | 生成符合 SkillHub 规范的技能文档 |
| 4 | 置信度提示 | 对不确定字段标注 `[需核实:字段名]`，不编造内容 | 当规则语义模糊时，明确提示用户确认 |
| 5 | 批量处理与自定义格式 | 支持多文件批量转换，允许用户指定输出模板 | 一次转换 10 个框架规则文件 |

### 不能做（明确限制）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行代码 | 本 Skill 仅生成文档，不运行或测试代码 |
| 2 | 不保证规则完整性 | 源规则若有缺失或矛盾，转换结果同样存在缺陷 |
| 3 | 不替代人工审查 | 生成结果需用户自行复核，特别是安全敏感场景 |
| 4 | 不处理二进制文件 | 仅支持文本类输入（`.md`、`.txt`、`.json`、`.yaml`、`.mdc` 等） |

### 适用对象

- **目标用户**：使用 Claude Code 的开发者、技术团队负责人、DevOps 工程师
- **输入材料**：Cursor 规则文件（`.mdc`）、框架官方文档 URL、自定义规则文本
- **输出产物**：符合 SkillHub 规范的 `SKILL.md` 文档


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

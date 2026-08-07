---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: cursor-handbook
name: cursor-handbook
displayName: Cursor规则 结构化转换 技能手册
description: 将Cursor IDE规则集转化为可查询、可校验、可执行的结构化技能文档。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/cursor-handbook
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: skill-forge-studio
agent_created: true
trigger_words: ["cursor-handbook", "cursor 手册", "规则引擎", "cursor 规则", "cursor 技能", "规则转换", "规则结构化"]
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

# Cursor 规则结构化转换技能手册

## 一、能力边界（一页纸速查卡）

### 1.1 本技能能做什么

| 能力项 | 说明 | 输入要求 | 输出产物 |
|--------|------|----------|----------|
| 规则解析 | 读取 Cursor IDE 的 `.cursor/rules` 目录下的规则文件（`.mdc` 格式） | 规则文件路径或目录路径 | 结构化规则清单（YAML/JSON） |
| 规则校验 | 检查规则文件的语法完整性、引用有效性、命名规范性 | 规则文件内容 | 校验报告（含错误码与修正建议） |
| 规则转换 | 将规则文件转换为 Markdown 技能文档（SKILL.md 格式） | 规则文件内容 + 目标文档模板 | 完整的 SKILL.md 文档 |
| 规则查询 | 按关键词、场景、优先级检索规则内容 | 查询条件（关键词/场景标签） | 匹配的规则条目列表 |
| 规则执行辅助 | 生成规则对应的操作步骤清单，辅助 IDE 配置 | 规则条目 | 可执行的操作步骤序列 |

### 1.2 本技能不能做什么

| 限制项 | 说明 |
|--------|------|
| 不修改 IDE 配置 | 本技能仅生成文档与建议，不直接写入 Cursor IDE 的配置文件 |
| 不执行代码 | 不运行、编译、测试任何代码，仅做静态分析与文档生成 |
| 不保证规则效果 | 不承诺规则转换后一定能提升开发效率或代码质量 |
| 不处理非规则文件 | 不解析 `.cursor` 目录下的其他配置文件（如 `mcp.json`、`settings.json`） |
| 不跨 IDE 迁移 | 不生成适用于 VS Code、JetBrains 等其他 IDE 的规则格式 |

### 1.3 适用对象

| 对象类型 | 适用场景 | 使用方式 |
|----------|----------|----------|
| Cursor IDE 使用者 | 想整理、备份、分享自己的规则集 | 提供规则目录路径，获取结构化文档 |
| 团队技术负责人 | 统一团队规则规范，便于新成员快速上手 | 批量转换团队规则为技能文档 |
| 规则开发者 | 调试、优化规则文件结构 | 使用校验功能定位问题 |
| 技能文档创作者 | 将 Cursor 规则作为素材，生成新的技能文档 | 使用转换功能生成 SKILL.md |


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: cursor-handbook
name: cursor-handbook
displayName: 规则引擎 配置手册 技能编排
description: 将Cursor IDE规则集转化为可查询、可校验、可执行的结构化技能文档。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/cursor-handbook
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["cursor-handbook", "cursor 手册", "规则引擎", "cursor 规则", "cursor 技能", "cursor 配置", "cursor 命令"]
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

# Cursor Handbook — 规则引擎技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 本技能能做什么

| 序号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| 1 | 数据/文件/URL 结构化转换 | 将原始文本、配置文件或网页链接解析为结构化字段 | 一段 Markdown 规则文本、`rules.json`、GitHub 仓库 URL |
| 2 | 关键信息识别与保留 | 自动提取规则名称、触发条件、动作、优先级、依赖关系 | 规则片段中的 `when` / `then` 子句 |
| 3 | 约定格式输出 | 按预定义模板生成 Markdown 表格、JSON 或 YAML 文档 | 输出为 `rules_summary.md` 或 `rules_export.json` |
| 4 | 置信度标注 | 对提取结果标注可信程度（高/中/低），不确定字段显式标记 | `confidence: 0.85` 或 `[需核实: 规则优先级]` |
| 5 | 批量处理与自定义格式 | 支持多文件批量解析，允许用户指定输出模板 | 传入 `--batch` 参数处理整个 `rules/` 目录 |

### 1.2 本技能不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行规则 | 本技能仅解析、整理、输出文档，不实际运行或触发 Cursor IDE 中的任何规则 |
| 2 | 不修改原始文件 | 所有操作均为只读，输出结果写入新文件或标准输出 |
| 3 | 不保证规则正确性 | 对规则逻辑本身的正确性不做判断，仅做结构化呈现 |
| 4 | 不支持二进制格式 | 仅处理纯文本、Markdown、JSON、YAML 等可读格式 |

### 1.3 适用对象

- Cursor IDE 使用者：需要梳理、归档、迁移自己的规则集
- 团队技术负责人：需要统一规则格式，便于审查与版本管理
- 技能开发者：需要将现有规则集转换为可复用的 Skill 文档


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

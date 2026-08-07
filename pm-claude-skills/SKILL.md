---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: pm-claude-skills
name: pm-claude-skills
displayName: 产品研发 技能编排 全栈工具箱
description: 面向产品经理的Agent技能库，覆盖文档生成、数据分析与流程自动化。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/pm-claude-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["pm-claude-skills", "产品技能", "技能编排", "PM工具箱", "技能库导航"]
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

# pm-claude-skills — 产品研发技能编排工具箱

## 一、能力边界速查卡

本 Skill 是一套面向产品经理与研发协作场景的技能导航与执行框架。它不替代具体业务工具，而是提供一套标准化的调用方式，帮助你在 Claude、ChatGPT、Gemini、Cursor 或 Codex 等 Agent 环境中，快速定位并执行合适的技能流程。

| 维度 | 说明 |
|------|------|
| **核心用途** | 将用户输入的数据、文件或 URL 转化为结构化输出（如 PRD、复盘报告、需求拆解） |
| **输入来源** | 用户直接粘贴的文本、上传的文档、可访问的 URL 链接 |
| **输出格式** | 支持 Markdown、JSON、CSV 等常见格式，字段结构可自定义 |
| **处理能力** | 单条处理与批量处理均支持；可识别关键信息并保留上下文 |
| **置信度标注** | 对不确定字段输出 `[需核实:字段名]` 占位符，不编造内容 |

### 不能做的事

- 不能直接访问你本地的私有文件系统（需通过 Agent 平台的文件上传接口）
- 不能执行需要登录态的第三方平台操作（如直接修改线上 PRD 文档）
- 不能保证输出结果的业务正确性——最终判断权在用户手中
- 不能替代人工评审与决策流程

### 适用对象

- 产品经理：快速生成 PRD、竞品分析、用户故事
- 研发工程师：解析需求文档、生成技术方案初稿
- 项目经理：整理复盘报告、风险清单、会议纪要
- 任何需要将零散信息整理为结构化文档的办公场景


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

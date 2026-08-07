---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agent-rules-books
name: agent-rules-books
displayName: 编码智能体规则手册 规范速查
description: 为AI编码智能体提供规则书与技能的结构化解析与生成服务。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agent-rules-books
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["AGENTS.md", "coding agent rules", "AI编码规范", "技能文档生成", "规则书解析"]
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

# agent-rules-books — 编码智能体规则手册

## 一、能力边界速查卡

本 Skill 面向需要快速整理、转换或生成 AI 编码智能体（如 Codex、Cursor、Claude Code）规则文档的用户。以下用一页纸说明它能做什么、不能做什么。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入处理 | 接受用户粘贴的文本、上传的文件路径、或公开 URL 指向的规则文档 | 无法主动联网抓取未明确提供的资源；无法读取本地私有文件（需用户显式提供路径） |
| 信息提取 | 识别规则文档中的关键约束、目录结构、命令示例、命名约定 | 不推断文档中未写明的隐含规则；不猜测作者意图 |
| 格式转换 | 将非结构化文本转换为 Markdown 表格、清单、决策树等结构化表达 | 不生成可执行代码；不直接修改用户的 AGENTS.md 文件 |
| 输出控制 | 按用户指定的字段顺序与层级输出；支持批量处理多个文档片段 | 不输出超出输入范围的新增规则；不生成虚构的引用来源 |
| 质量反馈 | 对每个输出字段标注置信度（高/中/低）；对缺失信息给出 `[需核实:字段]` 占位 | 不编造缺失值；不保证输出结果通过任何第三方审核 |

**适用对象**：需要为团队维护编码规范文档的工程师、准备将项目规则导入 AI 工具链的技术负责人、以及需要对比多份规则文档差异的分析人员。


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

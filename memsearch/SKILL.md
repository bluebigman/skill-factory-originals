---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: memsearch
name: memsearch
displayName: 记忆检索 跨会话持久化 语义查询
description: 基于Markdown与Milvus的统一记忆层，为AI代理提供持久化语义检索。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/memsearch
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge
agent_created: true
trigger_words: ["memsearch", "记忆检索", "语义搜索", "持久记忆", "跨会话记忆", "向量查询"]
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

# memsearch — 跨会话持久化记忆检索 Skill

## 一、能力边界速查卡

本 Skill 面向需要跨会话保留与检索信息的 AI 代理（如 Claude Code、Codex）或开发者，提供基于 Markdown 文件与 Milvus 向量数据库的统一记忆层操作能力。

| 维度 | 说明 |
|------|------|
| **核心功能** | 将输入数据（文本/文件/URL）解析、结构化、向量化后写入记忆库；支持语义查询与召回 |
| **输入来源** | 用户直接提供的数据片段、本地文件路径、可访问的 URL |
| **输出格式** | 结构化 JSON 或 Markdown 表格，包含字段、置信度标注 |
| **批量处理** | 支持一次摄入多个条目，自动去重与索引 |
| **自定义扩展** | 允许用户指定输出字段结构或过滤条件 |

### 能做（5 项）

1. **数据摄入**：将用户提供的文本、文件内容或 URL 抓取内容，解析为结构化条目。
2. **关键信息提取**：自动识别实体、时间、主题标签等关键字段，存入记忆条目。
3. **语义检索**：基于自然语言查询，通过 Milvus 向量相似度召回最相关的记忆片段。
4. **置信度标注**：对每条检索结果或提取字段给出 0~1 的置信度分数，低置信度明确提示。
5. **批量与自定义**：支持多条目批量写入，允许用户自定义输出字段模板。

### 不能做（5 项）

1. **不执行外部系统写操作**：不直接修改用户文件系统以外的数据库或应用状态。
2. **不保证检索绝对准确**：语义检索基于向量相似度，存在误召回可能。
3. **不处理非文本内容**：图片、音视频等二进制内容需先经外部工具转文本。
4. **不自动删除记忆**：删除操作需用户显式指定条件或 ID。
5. **不跨 Skill 共享状态**：记忆库独立，不与其他 Skill 自动联动。

### 适用对象

- 使用 AI 编程助手进行长周期项目开发的工程师。
- 需要维护多轮对话上下文的应用开发者。
- 希望为 AI 代理构建持久化知识库的技术团队。


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

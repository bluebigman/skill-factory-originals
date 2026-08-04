---
slug: agent-memory-hub
name: agent-memory-hub
displayName: 团队记忆资产 四类归档 共享索引
description: 将对话、文档、代码整理为四类记忆资产，生成团队共享索引。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agent-memory-hub
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨
agent_created: true
trigger_words: 记忆整理, 知识库构建, 代码图谱, 团队索引, 资产归档, 记忆中枢, 知识沉淀
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 团队记忆资产 四类归档 共享索引

## 一、Skill 概览

本 Skill 用于将零散的对话记录、项目文档、代码片段等原始材料，系统性地整理为四类可复用的团队知识资产：**聊天记忆**、**可执行技能**、**大模型知识库**与**代码关系图谱**。整理完毕后，自动生成一份团队共享的记忆索引文件，方便后续检索与复用。

适用场景：项目复盘、新人培训资料准备、团队知识库建设、代码库结构梳理、跨项目经验沉淀。

## 二、前置条件

在调用本 Skill 之前，请确认以下条件已满足：

1. **输入材料已就绪**：用户已提供至少一份原始材料，形式可以是对话文本、文档文件（如 .md、.txt、.pdf）、代码文件（如 .py、.js、.java）或可访问的 URL 链接。
2. **格式约定明确**：用户已确认输出格式要求，或同意使用本 Skill 的默认输出格式（四类资产各自独立文件 + 一份索引文件）。
3. **权限与路径**：当前工作环境允许创建新文件，且用户已指定或同意使用默认输出目录（如 `./memory_assets/`）。
4. **批量处理确认**：若输入包含多个文件或 URL，用户已确认一次性批量处理，并知晓每份材料将独立生成资产条目。

## 三、执行步骤

### 步骤 1：收集与确认输入

- 接收用户提供的原始材料，包括文件路径、URL 列表或直接粘贴的文本内容。
- 向用户复述输入清单，确认材料完整且无遗漏。
- 若输入格式不符合预期（例如文件损坏、URL 无法访问），立即返回错误说明，并附上正确的输入格式示例。

### 步骤 2：解析与识别关键信息

对每一份输入材料执行以下解析操作：

- **对话文本**：提取发言人、时间戳（如有）、核心议题、结论、待办事项。
- **文档内容**：提取标题、章节结构、关键定义、重要数据、引用来源。
- **代码文件**：提取函数/类定义、模块依赖关系、对外接口、关键算法逻辑。
- **URL 页面**：提取页面标题、主要内容文本、内嵌链接、更新时间。

解析过程中，对不确定或模糊的信息（如缺失时间戳、代码注释不完整）予以标记，并在后续输出中标注置信度。

### 步骤 3：分类归档为四类资产

根据解析结果，将内容归入以下四个类别：

| 资产类别 | 归档规则 | 输出文件建议命名 |
|----------|----------|------------------|
| 聊天记忆 | 保留对话上下文、关键决策、未解决问题、行动项 | `chat_memory_<日期>.md` |
| 技能 | 将可复用的操作流程、方法论、代码模板提炼为步骤化说明 | `skill_<技能名>.md` |
| LLM 知识库 | 整理为问答对、概念解释、事实性知识条目 | `knowledge_<主题>.md` |
| 代码图谱 | 用结构化文本描述模块关系、调用链、数据流 | `code_map_<项目名>.md` |

每条资产条目需包含：来源标识（原始文件/URL）、提取时间、置信度评分（高/中/低）。

### 步骤 4：生成结果并校验完整性

- 将四类资产分别写入独立文件。
- 检查每个文件是否符合约定的字段结构：
  - 聊天记忆：`[时间] 发言人：内容` 逐条列出。
  - 技能：包含 `适用场景`、`操作步骤`、`注意事项` 三个小节。
  - 知识库：每条包含 `问题` 与 `答案` 两个字段。
  - 代码图谱：包含 `模块清单`、`依赖关系`、`关键函数说明` 三个部分。
- 逐项核对字段是否存在遗漏，格式是否统一，置信度标注是否完整。

### 步骤 5：生成团队共享记忆索引

- 在输出目录下创建 `_INDEX.md` 文件。
- 索引中列出所有生成的资产文件名、对应的类别、简要描述、生成日期。
- 索引末尾附上使用说明：如何根据索引快速定位所需资产。

### 步骤 6：交付与二次确认

- 将全部生成文件的路径列表呈现给用户。
- 若用户对某些条目的置信度有疑问，或需要调整分类方式，重新执行相关步骤。
- 确认无误后，本次整理工作结束。

## 四、输出说明

**输出目录结构示例：**

```
memory_assets/
├── _INDEX.md
├── chat_memory_2025-01-15.md
├── skill_代码审查流程.md
├── knowledge_API设计原则.md
└── code_map_订单服务.md
```

**每个资产文件的内容格式**：顶部为元信息区（来源、生成时间、置信度），下方为正文区（按类别规则组织）。

**索引文件格式**：Markdown 表格，列为 `文件名 | 类别 | 内容摘要 | 生成日期`。

## 五、失败处理与异常应对

| 异常情况 | 处理方式 |
|----------|----------|
| 输入文件无法解析（如二进制损坏） | 跳过该文件，在索引中记录“解析失败”，并告知用户重新提供有效文件 |
| 输入内容过于简短（不足 50 字） | 提示用户内容过少，可能无法提取有效资产，询问是否继续 |
| 用户未指定输出格式 | 使用默认格式，并在交付时说明所采用的格式约定 |
| 分类存在歧义（一条内容可归多类） | 默认归入“知识库”，同时在其他相关资产文件中添加交叉引用链接 |
| 置信度低于 30% 的条目 | 单独列入文件末尾的“低置信度待确认”区域，并在交付时提醒用户审核 |
| 批量处理中途失败 | 保留已成功生成的资产文件，重新运行时可跳过已完成项 |

## 六、使用建议

- 建议每次整理后，将索引文件同步至团队共享文档平台，确保全员可访问。
- 对于高频更新的项目，建议每周执行一次本 Skill，保持记忆库的时效性。
- 低置信度的条目不要直接删除，留作待确认状态，由领域专家二次审核后再决定去留。
- 代码图谱类资产建议与 CI/CD 流程结合，每次代码合并后自动触发更新。

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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: lanshu-awesome-ai-video-kit
name: lanshu-awesome-ai-video-kit
displayName: 企业视频制作 智能工具包
description: 面向企业AI视频项目的结构化处理工具包，支持数据解析、批量转换与置信度标注。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/lanshu-awesome-ai-video-kit
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LanShu Studio
agent_created: true
trigger_words: ["lanshu awesome ai video kit", "AI视频工具包", "视频项目处理", "企业视频工作流", "视频数据转换"]
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

# 企业视频制作 智能工具包（SKILL.md）

## 一、能力边界：一页纸速查卡

本工具包面向企业 AI 视频项目的日常数据处理场景，提供一套可复用的结构化处理流程。以下是能力速查：

| 维度 | 说明 |
|------|------|
| **核心定位** | 将用户提供的原始数据（文本/文件/URL）转换为符合约定格式的结构化结果 |
| **适用对象** | 视频项目制片人、内容运营、后期剪辑协调员、AI 视频工具链使用者 |
| **输入类型** | 用户直接粘贴的文本、上传的本地文件（.txt/.csv/.json/.md）、可访问的 URL |
| **输出类型** | 结构化 Markdown 表格、JSON 字段映射、带置信度标注的处理报告 |
| **批量能力** | 支持同一批次最多 20 条独立输入，逐条处理并汇总输出 |
| **自定义格式** | 用户可在请求中附带 `output_schema` 参数，指定输出字段结构 |

### 能做（5 项核心能力）

1. **数据解析与结构化**：从非结构化文本中提取关键实体（项目名、时间节点、角色、预算、素材路径等），映射为字段化输出。
2. **关键信息保留**：在转换过程中完整保留输入中的专有名词、数字、日期、URL 等不可丢失的信息，不做语义压缩。
3. **约定格式输出**：严格按照用户指定的字段结构或默认模板生成输出，支持 Markdown 表格与 JSON 两种格式。
4. **置信度提示**：对自动推断的字段（如分类、优先级、标签）标注置信度等级（高/中/低），低置信度项附注原因。
5. **批量处理与自定义适配**：支持多条目批量处理，允许用户通过 `output_schema` 覆盖默认输出结构。

### 不能做（明确边界）

| 边界项 | 说明 |
|--------|------|
| 不生成视频内容 | 本工具包不涉及视频画面、脚本创作或 AI 生成视频的实际渲染 |
| 不访问需登录的网页 | 仅处理公开可访问的 URL，无法绕过认证或付费墙 |
| 不执行代码 | 不运行用户上传的脚本或程序，仅做文本层面的解析与转换 |
| 不保证数据准确性 | 对输入中缺失或矛盾的信息，以 `[需核实:字段]` 占位标注，不做臆测补全 |
| 不处理非文本文件 | 图片、音频、视频文件本身不在处理范围内，仅支持包含文本内容的文件 |


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

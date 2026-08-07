---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: rtk-token-saver
name: rtk-token-saver
displayName: 令牌精简 代码压缩 上下文瘦身
description: 压缩代码与对话上下文，减少 LLM Token 消耗，适配主流 AI 编码工具。
version: 1.0.5
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/rtk-token-saver
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["rtk-token-saver", "token压缩", "上下文精简", "代码摘要", "对话压缩", "令牌节省"]
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

# rtk-token-saver — 令牌精简器

## 一、能力边界（速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 适用场景 |
|--------|------|----------|
| 代码上下文压缩 | 将大文件/多文件代码库压缩为语义等价的高密度摘要，保留函数签名、类结构、关键逻辑、TODO 标记 | 向 LLM 提问前，压缩项目代码作为上下文 |
| 对话历史精简 | 将冗长的多轮对话压缩为结构化要点，保留决策记录、待办事项、用户偏好、已确认的约束条件 | 长会话续接、跨会话上下文传递 |
| 文档智能摘要 | 将长文档（README、API 文档、设计文档）压缩为结构化摘要，保留标题层级、关键定义、使用示例 | 快速理解新项目、文档检索 |
| URL 内容提取 | 从公开网页 URL 提取正文内容并压缩为要点（需网络可用，支持 http/https） | 参考在线文档、技术博客 |
| 批量文件处理 | 一次处理多个文件/目录，按统一规则压缩并输出汇总报告，失败文件单独列出 | 大型代码库整体压缩 |
| 自定义压缩策略 | 通过参数调整压缩率（保守/标准/激进），控制信息保留粒度 | 不同场景对信息密度要求不同 |
| 结构化输出 | 支持输出为 Markdown / JSON / 纯文本三种格式 | 后续程序化处理、人工阅读 |
| 多轮迭代压缩 | 对超大文本（>100K token）支持分块压缩后合并 | 超大文件处理 |
| 自定义保留规则 | 通过 `--keep` 参数指定必须保留的关键词/正则表达式 | 保留关键标记、特定模式 |
| 压缩前后对比报告 | 输出压缩率、保留率、置信度分布 | 质量审计、效果评估 |

### 1.2 不能做什么

- **不能理解语义**：压缩基于统计与结构规则，不进行语义推理
- **不能保证无损**：压缩必然有信息损失，激进策略损失更大
- **不能处理私有协议**：仅支持 http/https URL，不支持其他协议
- **不能离线处理 URL**：URL 提取需要网络连接
- **不能处理二进制文件**：仅支持文本文件
- **不能保证跨语言**：对非英语/中文内容的压缩效果可能下降

### 1.3 适用对象

- 使用 AI 编码工具（如 Cursor、Copilot、Continue 等）的开发者
- 需要频繁向 LLM 传递大量上下文的工程师
- 处理大型代码库、长文档的技术人员
- 对 Token 成本敏感的个人开发者或团队


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

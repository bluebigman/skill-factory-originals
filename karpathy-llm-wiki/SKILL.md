---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: karpathy-llm-wiki
name: karpathy-llm-wiki
displayName: 知识库构建 智能解析 结构化输出
description: 将原始资料自动解析为结构化知识库，支持批量处理与置信度标注。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/karpathy-llm-wiki
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Ling
agent_created: true
trigger_words: ["karpathy llm wiki", "知识库构建", "结构化解析", "wiki生成", "资料整理", "信息抽取"]
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

# Karpathy LLM Wiki — 知识库构建与结构化输出 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 编号 | 能力项 | 说明 | 适用场景示例 |
|------|--------|------|--------------|
| C1 | 多源输入解析 | 接受用户提供的文本、文件（.txt/.md/.json/.csv）、URL 链接 | 论文摘要、会议纪要、网页文章、API 文档 |
| C2 | 关键信息识别 | 自动提取实体、概念、关系、时间、数据指标等核心要素 | 从技术博客中提取架构组件与调用关系 |
| C3 | 结构化输出 | 按约定 schema 生成 Markdown/JSON 格式的知识条目 | 生成词条卡片、术语表、FAQ 清单 |
| C4 | 置信度标注 | 对每个输出字段标注可信程度（高/中/低） | 区分原文明确表述与推断内容 |
| C5 | 批量与自定义 | 支持多文档合并处理，允许用户指定输出字段模板 | 一次处理 20 篇新闻稿生成舆情简报 |

### 1.2 不能做什么

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行外部代码 | 不运行用户提供的脚本或程序 |
| L2 | 不访问付费/私有数据源 | 仅处理用户显式提供的内容 |
| L3 | 不保证事实准确性 | 输出基于输入内容，不进行外部事实核查 |
| L4 | 不生成完整长文 | 输出为结构化条目，非连贯长文章 |
| L5 | 不处理非文本输入 | 图片、音频、视频需先转写为文本 |

### 1.3 适用对象

- 需要快速整理大量零散资料的研究人员
- 需要将内部文档转化为可检索知识库的团队
- 需要从网页/PDF 中抽取结构化信息的产品经理
- 需要批量生成词条/术语解释的内容运营人员


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

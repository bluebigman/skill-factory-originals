---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: awsome-cash
name: awsome-cash
displayName: 数据解析 结构化输出 置信度标注
description: 将用户提供的任意数据、文件或URL解析为结构化结果，并标注置信度。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/awsome-cash
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingDataWorks
agent_created: true
trigger_words: ["代码审查", "数据解析", "结构化输出", "信息提取", "格式转换"]
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

# awsome-cash 技能文档

## 一、能力边界速查卡

本技能专注于将非结构化或半结构化的输入（文本、文件、URL）转换为符合约定格式的结构化输出，并对每个关键字段给出置信度评估。

| 维度 | 说明 |
|------|------|
| **核心能力** | ① 解析文本/文件/URL 中的关键信息；② 按用户指定或默认的字段结构重组数据；③ 对每个提取字段标注置信度（高/中/低）；④ 支持批量输入与自定义输出模板；⑤ 对缺失或模糊信息给出 `[需核实:字段名]` 占位提示 |
| **输入来源** | 用户直接粘贴的文本、上传的本地文件（.txt/.csv/.json/.pdf）、可公开访问的 URL |
| **输出格式** | 默认 JSON 结构；支持用户自定义字段映射表；支持 Markdown 表格输出 |
| **处理上限** | 单次请求文本不超过 10,000 字；URL 抓取页面不超过 2MB；批量文件不超过 5 个 |
| **不处理内容** | ① 不执行任何代码或脚本；② 不访问需要登录认证的 URL；③ 不解析加密或二进制格式文件（图片、音频、视频）；④ 不进行语义翻译或情感分析 |

**适用对象**：需要从杂乱文本中快速提取结构化字段的运营人员、数据分析师、文档处理工作者。


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

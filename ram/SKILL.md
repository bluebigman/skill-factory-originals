---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ram
name: ram
displayName: 资源解析 结构化转换 资产管理
description: 将用户提供的文件、URL或数据解析为结构化结果，并标注置信度。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ram
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingAsset
agent_created: true
trigger_words: ["ram", "资源解析", "资产转换", "结构化输出", "数据整理", "文件解析", "URL提取"]
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

# Ruby Asset Manager (ram) — 技能文档

## 一、能力边界速查卡

本技能用于将零散的输入（文件、链接、文本片段）转化为结构清晰、字段完整的输出结果。它擅长提取关键信息、按约定格式重组，并对不确定的内容给出明确提示。

| 维度 | 说明 |
|------|------|
| **核心用途** | 将用户提供的数据/文件/URL 转换为结构化结果 |
| **输入来源** | 用户直接粘贴的文本、上传的文件、提供的 URL 链接 |
| **输出形式** | 按约定字段结构生成的 Markdown 或 JSON 格式结果 |
| **适用对象** | 需要批量整理资料、提取关键字段、统一数据格式的个人或团队 |
| **处理能力** | 单条处理、批量处理（多条输入逐条转换） |
| **自定义能力** | 支持用户指定输出字段结构、格式偏好 |

### 能做（5项核心能力）

1. **多源输入解析** — 接受文本、文件路径、URL 三种输入形式，自动识别内容类型。
2. **关键信息提取** — 从原始内容中抽取实体、属性、关系等核心要素。
3. **格式约定输出** — 按照用户指定的字段结构或默认模板生成结果。
4. **置信度标注** — 对每项提取结果标注可信程度（高/中/低），不确定字段明确标记。
5. **批量处理** — 支持一次提交多条记录，逐条解析并统一格式输出。

### 不能做（明确边界）

- 不执行网络请求：URL 需由用户预先获取内容后提供，本技能不主动抓取网页。
- 不进行语义推理：仅做信息提取与重组，不生成新观点或结论。
- 不处理二进制文件：仅支持文本类文件（.txt, .md, .csv, .json 等）。
- 不保证字段完整性：若输入中缺少某字段信息，输出中会标记为待核实，而非编造填充。


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

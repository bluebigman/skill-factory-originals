---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: e2m
name: e2m
displayName: 文档转Markdown 格式转换 内容提取
description: 将多种格式文件或链接转换为结构化Markdown，保留关键信息。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/e2m
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 墨规
agent_created: true
trigger_words: ["e2m", "转markdown", "转md", "文件转换", "格式转换", "提取内容"]
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

# E2M 技能文档（SKILL.md）

## 一、能力边界速查卡

本技能用于将常见办公与网页文件转换为 Markdown 格式，并提取结构化信息。以下表格明确列出支持与不支持的范围，请在使用前对照确认。

| 能力维度 | 支持（能做） | 不支持（不能做） |
| :--- | :--- | :--- |
| **输入格式** | `.doc`, `.docx`, `.epub`, `.html`, `.htm`, `.url`, `.pdf`, `.ppt`, `.pptx`, `.mp3`, `.m4a` | 加密文件、损坏文件、扫描版图片型 PDF（无 OCR 能力） |
| **输入来源** | 本地文件路径、标准 HTTP/HTTPS 链接 | 需要登录鉴权的私有链接、非标准协议链接 |
| **核心处理** | 提取正文文本、识别标题层级、保留表格结构、提取链接与图片引用 | 复杂排版还原（如文本框坐标、艺术字效果）、动态网页脚本执行 |
| **输出格式** | 标准 Markdown（`.md`），含标题、列表、表格、代码块、引用块 | 自定义模板渲染（如特定 CMS 格式）、PDF 直接输出 |
| **附加能力** | 批量处理（多文件依次转换）、音频文件基础转写（需网络服务） | 实时流式转写、说话人分离、情感分析 |
| **信息标注** | 对不确定的字段输出 `[需核实:字段名]` 占位符 | 自动填充缺失信息或编造内容 |

**适用对象**：需要将文档归档为纯文本格式的写作者、需要从网页或文档中提取关键信息的研究人员、需要批量整理资料库的内容运营人员。


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

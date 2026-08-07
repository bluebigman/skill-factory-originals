---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: pdf-to-markdown
name: pdf-to-markdown
displayName: PDF结构化 表格还原 文档转换
description: 将PDF解析为带表格结构的Markdown，保留版式与关键信息。
version: 2.0.6
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/pdf-to-markdown
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 墨斗研习社
agent_created: true
trigger_words: ["pdf转markdown", "pdf转md", "pdf表格提取", "pdf解析", "pdf转文档", "表格还原"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# PDF 转 Markdown 技能手册

## 一、能力边界速查卡

本技能用于将 PDF 文件内容转换为结构化的 Markdown 文档，重点处理表格、标题层级、列表与代码块的还原。

| 能力维度 | 支持情况 | 说明 |
|---------|---------|------|
| 文本提取 | ✅ 支持 | 可识别正文、页眉页脚、脚注 |
| 表格还原 | ✅ 支持 | 识别单元格边界，输出为 Markdown 表格 |
| 图片处理 | ⚠️ 有限支持 | 仅保留图片占位符，不进行 OCR 文字识别 |
| 扫描件 | ❌ 不支持 | 纯图片型 PDF 需先经 OCR 预处理 |
| 加密文件 | ❌ 不支持 | 需用户先解除密码保护 |
| 批量转换 | ✅ 支持 | 可一次传入多个文件路径 |
| 自定义格式 | ✅ 支持 | 可指定标题层级映射规则 |

**适用对象**：数字化生成的 PDF（电子文档导出）、含清晰表格的报表、论文、说明书。
**不适用对象**：手写扫描件、低分辨率图片型 PDF、含复杂合并单元格的财务报表。


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

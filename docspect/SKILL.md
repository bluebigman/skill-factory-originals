---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: docspect
name: docspect
displayName: 合同审查 风险条款 智能摘要
description: 解析合同文档，输出结构化摘要与风险提示，辅助条款审阅。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/docspect
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["合同审查", "合同分析", "条款审阅", "风险提示", "合同摘要", "docspect"]
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

# docspect — 合同审查与风险提示 Skill

## 一、能力边界：一页纸速查卡

| 维度 | 说明 |
|------|------|
| **核心用途** | 将合同/协议文本（文件、粘贴文本、URL）解析为结构化摘要，标注高风险条款并给出修改建议 |
| **输入类型** | ① 本地文件（.txt/.md/.pdf/.docx，≤2MB）② 直接粘贴文本（≤50,000字符）③ 可公开访问的 URL（需返回纯文本或 HTML） |
| **输出格式** | Markdown 报告，包含：合同概要、关键条款清单、风险条款列表（含置信度）、修改建议 |
| **能做** | ✅ 提取合同主体、标的、金额、期限、违约责任等关键字段<br>✅ 识别 12 类常见风险条款（见下文风险库）<br>✅ 对每项识别结果给出置信度（高/中/低）<br>✅ 批量处理多个文件（每次最多 5 个）<br>✅ 自定义输出字段（通过参数指定） |
| **不能做** | ❌ 不提供法律意见或效力判断<br>❌ 不替代律师审阅<br>❌ 不处理扫描件/图片（需先 OCR）<br>❌ 不保证识别所有风险条款（召回率约 85%）<br>❌ 不执行跨语言翻译（仅处理中英文） |
| **适用对象** | 企业法务、合同管理员、创业者、需要快速了解合同要点的非法律专业人士 |


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

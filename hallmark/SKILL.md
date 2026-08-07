---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: hallmark
name: hallmark
displayName: 内容甄别 原创校验 风格净化
description: 识别AI痕迹，净化文本风格，辅助原创性审查与内容校准。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/hallmark
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 知微工作室
agent_created: true
trigger_words: ["hallmark", "anti-ai-slop", "去AI味", "AI痕迹检测", "文本净化", "原创性检查"]
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

# hallmark — 内容甄别与风格净化 Skill

## 一、能力边界：一页纸速查卡

本 Skill 用于辅助识别文本中可能存在的 AI 生成痕迹，并提供风格净化的操作指引。它不替代专业判断，而是提供一套可复用的检查框架。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入处理 | 接受用户粘贴的文本、上传的 .txt/.md 文件、公开 URL 指向的正文内容 | 不处理图片、PDF 扫描件、加密文档 |
| 痕迹识别 | 标记过度工整的句式、高频连接词、模板化开头结尾、异常均匀的段落长度 | 不提供"是否由 AI 生成"的确定性结论（技术上无法证明） |
| 风格净化 | 给出具体修改建议：句式拆分、连接词替换、节奏调整、个性化表达注入 | 不自动改写全文（需用户确认后逐条应用） |
| 输出形式 | 生成结构化检查报告（JSON 或 Markdown 表格，用户二选一） | 不生成 Word/PDF 文件 |
| 批量处理 | 支持一次提交最多 5 个独立文本块，分别输出报告 | 不支持超过 5 个文本块的合并分析 |

**适用对象**：内容编辑、自媒体运营者、学术写作辅助人员、需要做原创性自查的创作者。

**不适用场景**：法律取证、学术不端判定、任何需要"确定性结论"的正式审查流程。


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

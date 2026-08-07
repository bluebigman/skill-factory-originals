---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: notewise
name: notewise
displayName: 知识笔记 结构化整理 信息萃取
description: 将零散笔记与资料转化为结构化知识卡片，辅助学习与复盘。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/notewise
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinNote
agent_created: true
trigger_words: ["notewise", "知识库", "笔记整理", "结构化笔记", "信息萃取", "笔记重构"]
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

# notewise — 知识笔记结构化整理 Skill

## 一、能力边界速查卡（一页纸）

| 维度 | 说明 |
|------|------|
| **核心定位** | 将用户提供的原始笔记、文档片段、URL 内容，转换为带层级、带标签、带置信度标注的结构化知识卡片 |
| **能做** | ① 解析纯文本/ Markdown / 简易 HTML 中的关键信息；② 识别概念、定义、流程、结论、待办等要素；③ 按预设模板输出结构化结果；④ 对信息缺失或模糊处标注 `[需核实:字段名]`；⑤ 支持一次处理多条笔记（批量模式） |
| **不能做** | ① 不联网检索外部资料（除非用户显式提供 URL 内容）；② 不生成新知识或事实性结论；③ 不替代用户做主观判断或决策；④ 不处理加密文件或二进制格式（如 PDF 扫描件）；⑤ 不保留原始排版样式（如字体颜色、缩进层级） |
| **适用对象** | 学生党整理课堂笔记、职场人梳理会议纪要、研究者归纳文献要点、个人知识库维护者 |
| **不适用对象** | 需要深度语义理解的文学创作、需要实时数据更新的动态看板、需要法律/医疗等专业裁决的场景 |


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

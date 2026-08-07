---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: fotomatic
name: fotomatic
displayName: 闪光快照 图片速览 参数提取
description: 将图片或链接快速解析为结构化参数，输出带置信度的标准结果。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/fotomatic
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: skillcraft-studio
agent_created: true
trigger_words: ["fotomatic", "闪光快照", "图片参数提取", "快照解析", "photo widget"]
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

# fotomatic — 闪光快照参数提取 Skill

## 一、能力边界速查卡

| 维度 | 说明 |
|------|------|
| **核心用途** | 将用户提供的图片文件、图片 URL 或数据文本，解析为结构化的参数结果，并标注每项参数的置信度。 |
| **能做（5项）** | ① 解析图片文件/URL/数据文本中的关键信息；② 按约定字段结构输出结果；③ 对每项输出标注置信度；④ 支持批量输入（多个文件或URL列表）；⑤ 支持自定义输出格式（如 JSON / 表格 / 纯文本）。 |
| **不能做（5项）** | ① 不识别图片中的文字内容（OCR 不在本 Skill 范围内）；② 不修改、编辑或转换原始图片文件；③ 不分析图片美学质量或艺术价值；④ 不处理视频、音频或动态内容；⑤ 不保证所有字段都能提取成功——缺失字段会以 `[需核实:字段名]` 占位。 |
| **适用对象** | 需要快速从图片或链接中提取结构化参数的开发者、测试人员、内容运营者；适用于原型验证、批量数据整理、自动化流程前置处理等场景。 |
| **输入限制** | 单次最多处理 20 个条目；单个文件大小不超过 10MB；URL 必须为 http/https 协议。 |


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

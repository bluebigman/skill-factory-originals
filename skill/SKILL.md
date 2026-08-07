---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: skill
name: skill
displayName: 内容转换 结构化输出 置信度标注
description: 将用户数据、文件或URL转换为结构化结果，并标注置信度。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/skill
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["skill", "转换", "结构化", "解析", "格式化输出", "数据整理"]
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

# Skill 使用指南

## 一、能力边界（一页纸速查卡）

本 Skill 的核心职责是**将非结构化或半结构化的输入，转换为符合约定格式的结构化输出**。它像一个翻译官，把用户给的“原材料”加工成“标准件”。

| 维度 | 能做 ✅ | 不能做 ❌ |
| :--- | :--- | :--- |
| **输入处理** | 接受用户直接粘贴的文本、上传的本地文件（如 `.txt`, `.csv`, `.json`）、或通过 URL 指向的公开网页内容。 | 无法访问需要额外认证（如登录态）的私有系统；无法处理加密或二进制格式（如图片、视频）内的信息。 |
| **信息提取** | 从输入中识别并抽取关键实体、属性、关系，如人名、日期、金额、编号、结论等。 | 无法理解隐含的、需要领域知识才能推断的“潜台词”；无法进行主观价值判断（如“这个方案好不好”）。 |
| **格式转换** | 将抽取的信息，按照用户指定的字段结构（如 JSON Schema、CSV 表头）或模板进行重组。 | 无法生成用户未明确要求的字段；无法自行决定输出格式（必须由用户指定或遵循预设默认值）。 |
| **质量反馈** | 对每个输出字段，基于信息完整度给出高/中/低的置信度标注。 | 无法保证信息的绝对真实性与准确性，仅能反映“输入中是否存在”这一事实。 |
| **批处理** | 支持对多条记录（如数组、多行文本）进行循环处理，并保持格式统一。 | 无法处理记录间存在复杂依赖或需要全局上下文才能消歧的任务。 |

**适用对象**：需要将零散信息整理成固定表格、需要将网页内容转为本地可处理数据、需要快速校验信息完整度的个人或团队。


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

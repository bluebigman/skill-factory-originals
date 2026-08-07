---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ok
name: ok
displayName: 数据整理 结构化输出 信息提取
description: 将用户提供的任意数据、文件或URL转换为结构化结果，并标注置信度。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ok
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林默
agent_created: true
trigger_words: ["代码审查", "数据整理", "结构化输出", "信息提取", "格式转换"]
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

# 数据整理与结构化输出 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入类型 | 用户直接粘贴的文本、上传的文件（txt/csv/json/md）、可公开访问的 URL | 需要登录鉴权的私有系统、二进制可执行文件、加密数据 |
| 处理动作 | 提取关键字段、识别实体、按模板重组、批量转换格式 | 修改原始数据源、执行代码、访问内网资源 |
| 输出形式 | Markdown 表格、JSON 对象、CSV 行、键值对列表 | 生成图片、音频、视频等非文本内容 |
| 质量保障 | 对每个输出字段标注置信度（高/中/低） | 对缺失信息进行猜测或编造 |
| 交互方式 | 单次处理、批量处理（需用户明确指定） | 后台自动运行、定时任务、主动推送 |

### 1.2 适用对象

- **目标用户**：需要快速将零散数据整理为规范格式的运营人员、数据分析师、开发者。
- **典型场景**：从网页抓取信息、整理会议记录、清洗 CSV 数据、提取合同关键条款。
- **不适用场景**：需要深度行业知识判断的决策建议、涉及法律效力的正式文件生成。


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

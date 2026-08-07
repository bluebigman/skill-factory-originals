---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: bedrock
name: bedrock
displayName: 数据解析 信息抽取 结构化输出
description: 将用户提供的任意数据转换为结构化结果，支持批量处理与置信度标注。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/bedrock
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林默
agent_created: true
trigger_words: ["bedrock", "数据解析", "结构化输出", "信息抽取", "批量处理"]
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

# bedrock 技能文档

## 一、能力边界速查卡

### 能做（5项核心能力）

| 编号 | 能力 | 说明 |
|------|------|------|
| 1 | 数据转结构化 | 将用户提供的数据/文件/URL 内容转换为 JSON 或表格等结构化结果 |
| 2 | 关键信息识别 | 自动提取输入中的关键字段，如名称、日期、金额、编号等 |
| 3 | 约定格式输出 | 按用户指定的字段结构或默认模板生成输出 |
| 4 | 置信度标注 | 对每个输出字段标注可信程度（高/中/低） |
| 5 | 批量处理 | 支持多组数据同时处理，输出统一格式的结果集 |

### 不能做（明确边界）

| 编号 | 限制 | 说明 |
|------|------|------|
| 1 | 不处理二进制文件 | 仅支持文本、常见文档（txt/csv/json）及可访问的 URL |
| 2 | 不执行外部调用 | 不主动访问网络资源，仅解析用户提供的 URL 内容 |
| 3 | 不修改原始数据 | 输出为独立结果，不改变用户输入文件 |
| 4 | 不保证绝对准确 | 对模糊信息给出置信度提示，不承诺 100% 正确 |

### 适用对象

- 需要快速整理非结构化文本的运营人员
- 需要批量提取信息的分析人员
- 需要将 URL 内容转为可复用数据的开发者


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

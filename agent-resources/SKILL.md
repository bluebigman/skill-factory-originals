---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agent-resources
name: agent-resources
displayName: 技能资源 采集转换 结构化输出
description: 将任意数据、文件或URL转换为结构化结果，支持批量处理与自定义格式。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agent-resources
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["agent-resources", "资源转换", "数据采集", "结构化输出", "批量处理", "自定义格式"]
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

# agent-resources 技能文档

## 一、能力边界速查卡

本技能用于将用户提供的各类输入（数据、文件、URL）转换为结构化结果。以下是能力边界的一页纸说明：

| 维度 | 说明 |
|------|------|
| **核心能力** | 解析输入内容 → 识别关键信息 → 按约定格式输出 → 标注置信度 |
| **输入类型** | 文本数据、常见文件格式（CSV/JSON/TXT/MD）、可访问的URL |
| **输出类型** | JSON、Markdown、纯文本结构化列表（用户可指定） |
| **批量处理** | 支持多文件或多条记录同时处理，输出合并结果 |
| **自定义格式** | 用户可指定字段结构、输出模板、排序规则 |
| **不能做** | 无法访问需登录的URL、无法处理加密文件、不执行代码、不进行语义推断以外的深度分析 |

**适用对象**：需要将零散数据整理为规范格式的开发者、数据分析师、文档编写者。


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: blerb-core
name: blerb-core
displayName: 数据解析 信息抽取 结构化输出
description: 将用户提供的数据、文件或URL解析为结构化结果，并标注置信度。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/blerb-core
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["blerb core", "数据解析", "结构化输出", "信息抽取", "内容转换"]
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

# blerb-core 技能文档

## 一、能力边界速查卡

本技能用于将非结构化或半结构化的输入（文本、文件、URL）转换为符合用户要求的结构化输出。以下表格明确列出本技能的支持范围与限制。

| 维度 | 支持（能做） | 不支持（不能做） |
|------|-------------|-----------------|
| 输入类型 | 纯文本、常见文本文件（.txt/.md/.csv/.json）、可公开访问的 URL 内容 | 二进制文件（图片/视频/音频）、加密文件、需要登录鉴权的私有 URL |
| 处理能力 | 提取关键字段、识别实体与关系、按模板重组内容、批量处理多个输入项 | 执行代码、修改原始文件、进行数值计算或逻辑推理、跨语言翻译 |
| 输出形式 | JSON、Markdown 表格、CSV、自定义分隔符文本 | 直接写入用户本地文件系统（需用户自行复制保存） |
| 交互方式 | 单轮指令、多轮澄清、批量输入（用空行或逗号分隔多个条目） | 实时流式输出、后台定时任务、主动推送通知 |

**适用对象**：需要快速将零散信息整理为固定格式的开发者、数据分析师、文档处理人员。不适用于需要深度语义理解或创造性写作的场景。


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

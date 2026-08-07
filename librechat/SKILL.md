---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: librechat
name: librechat
displayName: 对话增强 数据整理 格式转换
description: 将用户提供的任意数据、文件或链接，整理为结构化、可校验的规范输出。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/librechat
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["librechat", "数据整理", "结构化输出", "格式转换", "信息提取"]
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

# LibreChat 技能文档

## 一、能力边界：一页纸速查卡

本技能用于处理用户输入的原始材料（文本、文件、URL），将其转化为符合约定结构的结果。它不改变事实，只负责整理与呈现。

| 维度 | 说明 |
|------|------|
| **核心任务** | 解析输入 → 提取关键信息 → 按约定格式输出 |
| **输入类型** | 用户粘贴的文本、上传的文件（txt/md/csv/json）、可访问的 URL |
| **输出类型** | 结构化 Markdown 表格、JSON 对象、字段清单（取决于用户指定） |
| **批量能力** | 支持一次处理多条记录，但需用户明确分隔方式 |
| **置信度标注** | 对无法确认的字段，输出 `[需核实:字段名]` 占位符，不做猜测 |

**不能做的事：**

- 不访问需要登录凭证的私有系统
- 不执行代码或运行程序
- 不修改用户原始文件（仅生成新内容）
- 不保证提取结果与源文件逐字一致（涉及语义理解时存在误差可能）

**适用对象：** 需要快速将零散资料整理为统一格式的日常办公场景，如会议记录整理、简历信息提取、商品参数汇总、URL 内容摘要。


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

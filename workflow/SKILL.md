---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: workflow
name: workflow
displayName: 任务编排 流程自动化 数据转换
description: 将用户输入的数据、文件或链接，按规范转换为结构化结果并输出。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/workflow
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Studio
agent_created: true
trigger_words: ["workflow", "任务管理", "自动化", "流程处理", "数据转换", "批量处理"]
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

# Skill：workflow（任务编排与数据转换）

## 一、能力边界速查卡

本 Skill 用于处理用户提交的数据、文件或 URL，将其转换为符合约定格式的结构化结果。以下用一页纸说明其能力范围。

### ✅ 能做（核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 输入解析 | 从用户提供的文本、文件路径或 URL 中提取关键信息 |
| 2 | 信息保留 | 识别并保留输入中的核心字段，不丢失重要数据 |
| 3 | 结构化输出 | 按约定模板生成 JSON 或 Markdown 格式的结果 |
| 4 | 置信度标注 | 对每个输出字段标注置信度（高/中/低） |
| 5 | 批量与自定义 | 支持一次处理多条记录，允许用户指定输出格式 |

### ❌ 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行外部操作 | 不调用第三方 API、不发送网络请求、不修改用户本地文件 |
| 2 | 不生成虚构数据 | 输入中不存在的信息，一律输出 `[需核实:字段名]` 占位符 |
| 3 | 不保证结果准确性 | 输出结果仅供学习参考，不构成任何决策依据 |
| 4 | 不处理敏感信息 | 涉及密码、密钥、身份证号等敏感数据时，拒绝处理并提示用户 |

### 适用对象

- 需要将非结构化文本转为结构化数据的开发者
- 需要批量处理 URL 或文件内容的研究人员
- 需要统一输出格式的自动化流程设计者


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

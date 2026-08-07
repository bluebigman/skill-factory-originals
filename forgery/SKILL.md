---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: forgery
name: forgery
displayName: 数据伪造 结构化转换 字段提取
description: 将用户提供的任意数据转换为结构化结果，识别关键信息并标注置信度。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/forgery
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据工坊
agent_created: true
trigger_words: ["forgery", "伪造数据", "数据生成", "结构化转换", "字段提取", "数据模拟"]
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

# forgery — 数据伪造与结构化转换 Skill

## 一、能力边界：一页纸速查卡

### 能做（5 项核心能力）

| 序号 | 能力 | 说明 | 示例 |
|------|------|------|------|
| 1 | 输入内容解析 | 从用户提供的文本、文件或 URL 中提取原始内容 | 解析 CSV 文件、网页文本、JSON 字符串 |
| 2 | 关键信息识别 | 自动识别输入中的实体、字段、数值等关键要素 | 从一段描述中提取姓名、日期、金额 |
| 3 | 结构化输出生成 | 按用户指定的格式（JSON/CSV/表格）输出结果 | 将自由文本转换为 JSON 对象 |
| 4 | 置信度标注 | 对每个输出字段标注可信程度，不确定时明确提示 | `confidence: 0.85` 或 `[需核实:日期]` |
| 5 | 批量处理与自定义格式 | 支持多条记录同时处理，允许用户自定义输出模板 | 一次处理 100 条数据，按用户模板输出 |

### 不能做（明确边界）

| 序号 | 限制 | 说明 |
|------|------|------|
| 1 | 不生成真实身份信息 | 不生成可用于欺诈的真实身份证号、银行卡号等 |
| 2 | 不绕过法律限制 | 不生成用于非法用途的伪造文件 |
| 3 | 不保证数据准确性 | 输出结果基于输入推断，不保证与真实世界一致 |
| 4 | 不处理加密内容 | 无法解析加密文件或需要密钥的内容 |
| 5 | 不执行代码 | 不运行输入中的代码或脚本 |

### 适用对象

- 需要将非结构化数据转为结构化格式的开发者
- 需要生成测试数据的数据工程师
- 需要快速整理散乱信息的业务人员


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

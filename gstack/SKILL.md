---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: gstack
name: gstack
displayName: 数据整理 结构化转换 批量处理
description: 将用户提供的数据、文件或URL转换为结构化结果，支持批量处理与自定义格式。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/gstack
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 技能工坊
agent_created: true
trigger_words: ["gstack", "数据整理", "结构化转换", "批量处理", "格式转换"]
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

# gstack 技能文档

## 一、能力边界（一页纸速查卡）

### 能做（5项核心能力）

| 编号 | 能力项 | 说明 | 示例 |
|------|--------|------|------|
| 1 | 数据/文件/URL 转结构化结果 | 将非结构化输入转换为 JSON、CSV 等结构化格式 | 将一段文本中的联系人信息提取为表格 |
| 2 | 关键信息识别与保留 | 自动识别输入中的核心字段，保留上下文关联 | 从日志文件中提取时间戳、错误级别、错误码 |
| 3 | 按约定格式生成输出 | 支持指定输出格式（JSON/CSV/Markdown 表格等） | 指定 `format=csv` 输出逗号分隔文件 |
| 4 | 置信度标注 | 对识别结果给出置信度水平（高/中/低） | 字段 `confidence: 0.92` |
| 5 | 批量处理与自定义格式 | 支持多文件/多 URL 批量处理，可自定义字段映射 | 一次处理 10 个 URL，提取统一字段集 |

### 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行外部程序 | 不调用系统命令、不运行用户提供的代码 |
| 2 | 不访问付费 API | 仅处理用户直接提供的数据/文件/URL 内容 |
| 3 | 不做语义推断 | 不猜测未提供字段的含义，缺失字段标注 `[需核实:字段名]` |
| 4 | 不保证数据准确性 | 输出结果依赖输入质量，不承担数据验证责任 |
| 5 | 不处理敏感信息 | 不接收密码、密钥、身份证号等敏感数据 |

### 适用对象

- 需要将散乱数据整理为规范格式的开发者
- 需要批量提取网页/文档关键信息的研究人员
- 需要统一多来源数据结构的运维工程师


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

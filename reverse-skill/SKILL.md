---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: reverse-skill
name: reverse-skill
displayName: 数据逆向 结构化解析 字段还原
description: 将任意输入数据解析为结构化结果，保留关键信息并标注置信度。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/reverse-skill
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 技能工坊
agent_created: true
trigger_words: ["reverse skill", "逆向解析", "数据还原", "结构化转换"]
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

# reverse-skill 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|--------|----------|
| 输入类型 | 文本、JSON、CSV、URL 指向的公开数据 | 加密文件、需登录的私有数据、二进制大文件 |
| 处理能力 | 字段提取、类型识别、结构重组、批量转换 | 语义理解、情感分析、跨语言翻译 |
| 输出形式 | 结构化 JSON、Markdown 表格、CSV | 图表绘制、可视化仪表盘 |
| 质量保障 | 置信度标注、字段完整性检查、格式校验 | 数据真实性核验、外部事实核查 |
| 扩展能力 | 自定义字段映射、输出模板定制 | 实时流处理、分布式计算 |

### 1.2 适用对象

- **适合**：需要将非结构化数据转为结构化表格的开发者、需要批量清洗数据的分析师、需要快速还原接口返回结构的测试人员。
- **不适合**：需要深度业务洞察的场景、需要实时数据同步的场景、对数据准确性有绝对要求的场景。

### 1.3 输入输出速查

| 项目 | 说明 |
|------|------|
| 输入来源 | 用户直接粘贴文本、上传文件（≤5MB）、公开 URL |
| 输出格式 | 默认 JSON，可选 Markdown / CSV |
| 字段结构 | `{ "data": [...], "meta": { "confidence": 0.0-1.0, "warnings": [] } }` |
| 处理耗时 | 单条 < 1s，批量 1000 条 < 30s |


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: sequel-model
name: sequel-model
displayName: 数据建模 结构转换 字段映射
description: 将用户提供的任意数据源转换为结构化结果，支持批量处理与置信度标注。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/sequel-model
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 墨规
agent_created: true
trigger_words: ["sequel model", "数据建模", "结构转换", "字段映射", "结构化输出"]
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

# Sequel::Model 数据建模 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入处理 | 用户提供的数据、文件路径、URL 链接 | 主动抓取未授权的网络资源 |
| 数据解析 | 识别关键字段、提取结构化信息 | 解析加密或损坏的文件 |
| 格式转换 | 按约定模板输出 JSON/YAML/CSV | 输出未定义的格式 |
| 批量操作 | 支持多条记录同时处理 | 超过 1000 条记录的批处理 |
| 质量反馈 | 标注置信度、提示缺失字段 | 对不确定信息做主观臆断 |

### 1.2 适用对象

- 需要将非结构化数据转为结构化表格的开发者
- 需要批量清洗和映射字段的数据分析师
- 需要快速搭建数据管道的后端工程师


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: bun-sqlgen
name: bun-sqlgen
displayName: SQL查询生成 数据转换 批处理
description: 将输入数据转换为结构化SQL查询结果，支持批量处理与置信度标注。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/bun-sqlgen
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: QueryCraft Studio
agent_created: true
trigger_words: ["SQL查询", "bun sqlgen", "sqlgen", "数据库查询", "结构化输出", "数据转换"]
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

# bun-sqlgen 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做（核心能力清单）

| 编号 | 能力项 | 说明 | 适用场景 |
|------|--------|------|----------|
| C1 | 数据转结构化 | 将用户提供的原始数据（文本/文件/URL）转换为结构化结果 | 日志解析、CSV整理、网页数据提取 |
| C2 | 关键信息识别 | 从输入中提取并保留关键字段，去除冗余 | 用户查询意图识别、字段抽取 |
| C3 | 约定格式输出 | 按预定义模板生成统一格式的结果 | 报表生成、API响应格式化 |
| C4 | 置信度标注 | 对不确定的字段标注置信度水平 | 数据清洗、模糊匹配场景 |
| C5 | 批量与自定义 | 支持多批次输入处理及自定义输出模板 | 批量数据迁移、个性化报表 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行真实SQL | 本技能仅生成SQL查询文本，不连接数据库执行 |
| L2 | 不处理二进制数据 | 仅支持文本、JSON、CSV、URL等文本类输入 |
| L3 | 不保证数据准确性 | 输入数据本身的错误不在本技能修正范围内 |
| L4 | 不提供实时数据 | 所有输出基于用户提供的输入，不主动获取外部数据 |

### 1.3 适用对象

- 需要快速生成SQL查询语句的开发者
- 需要将非结构化数据转为结构化格式的数据分析师
- 需要批量处理数据文件的运维人员


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

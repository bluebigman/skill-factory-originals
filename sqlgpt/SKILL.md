---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: sqlgpt
name: sqlgpt
displayName: 自然语言转SQL 查询生成器
description: 将自然语言描述转换为可执行SQL查询语句，支持多表关联与方言适配。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/sqlgpt
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: QueryForge Studio
agent_created: true
trigger_words: ["SQL查询", "自然语言转SQL", "生成查询语句", "NL2SQL", "写SQL"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# SQLGPT — 自然语言转 SQL 查询生成器

## 一、能力边界速查卡

### 1.1 核心能力清单

| 序号 | 能力项 | 说明 | 输入要求 | 输出示例 |
|------|--------|------|----------|----------|
| 1 | 自然语言转SQL | 将中文/英文描述转换为标准SQL语句 | 描述查询意图，可附带表结构 | `SELECT * FROM users WHERE age > 18;` |
| 2 | 多表关联识别 | 自动识别JOIN条件与关联字段 | 提供多张表的字段清单 | `SELECT o.id, u.name FROM orders o JOIN users u ON o.user_id = u.id;` |
| 3 | 方言适配 | 支持 MySQL / PostgreSQL / SQLite / SQL Server | 指定目标数据库类型 | 输出对应方言的LIMIT/TOP语法 |
| 4 | 查询优化建议 | 对生成的SQL给出索引与性能提示 | 生成的SQL语句 | `建议在 orders.user_id 上建立索引` |
| 5 | 结果校验 | 检查SQL语法正确性与字段存在性 | 表结构定义（可选） | `语法通过，字段 user_name 不存在，已修正为 username` |

### 1.2 明确不做的事

- **不执行SQL语句**：仅生成与校验，不连接任何数据库。
- **不处理非结构化数据**：如纯文本日志、图片内容等。
- **不生成DML写操作**：仅支持 SELECT 查询，不生成 INSERT/UPDATE/DELETE。
- **不保证执行性能**：生成的SQL在特定数据量下的执行效率需自行评估。

### 1.3 适用对象

- 数据分析师：快速验证查询思路。
- 后端开发：减少手写SQL的重复劳动。
- 产品经理：自助取数，降低对技术团队的依赖。
- 学习者：通过自然语言理解SQL逻辑。


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

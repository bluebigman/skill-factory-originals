---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: sql-query-generator
name: sql-query-generator
displayName: 数据查询 SQL 语句生成器
description: 将自然语言或数据文件转换为可执行的SQL查询语句，支持无模式数据源。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/sql-query-generator
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Studio
agent_created: true
trigger_words: ["SQL查询", "查询生成", "sql builder", "无模式查询", "自然语言转SQL", "生成SQL", "写查询语句", "数据查询"]
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

# SQL 查询生成器 Skill 文档

## 一、能力边界（速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 自然语言转 SQL | 将中文/英文描述转换为标准 SQL 语句 | "查询最近7天订单量前10的商品" → SELECT ... |
| 数据文件结构识别 | 从 CSV/JSON/Excel 文件头推断字段类型与表结构 | 读取 CSV 首行，自动生成 CREATE TABLE 语句 |
| 无模式数据源适配 | 对没有预定义 schema 的数据源，先探测结构再生成查询 | 自动识别 JSON 嵌套字段并展开为列 |
| 多方言 SQL 生成 | 支持 MySQL、PostgreSQL、SQLite、SQL Server 等主流方言 | 自动调整分页语法、字符串拼接方式 |
| 查询优化建议 | 为生成的 SQL 附加索引建议和执行计划分析 | 对 WHERE 子句字段建议添加索引 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行 SQL | 本 Skill 只生成语句，不连接数据库执行 |
| 不处理敏感数据 | 不会读取或存储用户数据文件的实际内容，仅读取结构信息 |
| 不保证最优执行计划 | 生成的 SQL 基于规则优化，实际性能取决于数据库统计信息 |
| 不支持复杂存储过程 | 仅生成 DQL（查询）语句，不生成 DML/DDL 中的存储过程逻辑 |
| 不处理非结构化数据 | 对图片、音频、视频等非表格数据无法生成查询 |

### 1.3 适用对象

- 数据分析师：快速将业务问题转化为可执行查询
- 后端开发者：减少手写 SQL 的时间成本
- 产品经理：验证数据可行性，理解数据结构
- 数据运营：日常取数场景的提效工具


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

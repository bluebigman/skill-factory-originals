---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: sql-query-generator
name: sql-query-generator
displayName: 无模式SQL查询构建器
description: 将自然语言或数据文件转换为可执行的SQL查询语句，支持无模式数据源。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/sql-query-generator
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: QueryForge Studio
agent_created: true
trigger_words: ["SQL查询", "查询生成", "sql builder", "无模式查询", "自然语言转SQL", "query generator"]

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

# 无模式SQL查询构建器（sql-query-generator）

## 一、能力边界速查卡

### 1.1 能做什么

| 序号 | 能力项 | 说明 | 输入示例 | 输出示例 |
|------|--------|------|----------|----------|
| 1 | 自然语言转SQL | 将中文/英文描述转换为标准SQL语句 | "找出所有价格大于100的商品名称" | `SELECT name FROM products WHERE price > 100;` |
| 2 | 数据文件解析 | 从CSV/JSON/Excel中提取字段并生成建表及查询语句 | `data.csv` 含列 `id,name,price` | `CREATE TABLE ...; SELECT ...;` |
| 3 | URL数据提取 | 从API接口或网页中识别结构化数据并生成查询 | `https://api.example.com/items` | 基于返回JSON结构的查询语句 |
| 4 | 批量查询生成 | 一次处理多个查询需求，输出多条SQL | 5条查询描述 | 5条对应SQL语句 |
| 5 | 自定义格式输出 | 支持指定输出格式（纯SQL/带注释/JSON封装） | `--format json` | `{"query": "SELECT ...", "params": []}` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行SQL | 仅生成语句，不连接数据库执行 |
| 不优化已有SQL | 不接收SQL作为输入进行性能优化 |
| 不处理二进制数据 | 不支持图片、音视频等非结构化数据 |
| 不保证语法兼容 | 生成的SQL基于标准语法，特定数据库方言需自行调整 |
| 不推断缺失字段 | 输入中未明确提及的字段不会臆造 |

### 1.3 适用对象

- 需要快速生成查询语句的**后端开发者**
- 需要从数据文件中提取信息的**数据分析师**
- 需要将业务需求转化为SQL的**产品经理**
- 学习SQL语法的**初学者**


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: sqlw-mysql
name: sqlw-mysql
displayName: MySQL 代码生成 查询包装 文本转换
description: 为 MySQL 数据库与查询生成包装代码或文本源，支持批量与自定义格式。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/sqlw-mysql
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本 Skill 由 AI 辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Studio
agent_created: true
trigger_words: ["SQL查询", "--selftest", "--version", "MySQL 包装代码", "查询生成器", "SQL 文本转换"]
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

# SQLW-MySQL 技能文档

## 一、能力边界速查卡

### 能做（5 项核心能力）

| 序号 | 能力项 | 说明 | 示例 |
|------|--------|------|------|
| 1 | 输入解析 | 将用户提供的数据、文件内容或 URL 指向的文本解析为结构化中间表示 | 输入一段 SQL 查询文本，解析出 SELECT/FROM/WHERE 子句 |
| 2 | 关键信息识别 | 自动提取表名、字段名、连接条件、参数占位符等核心要素 | 从 `SELECT * FROM users WHERE id = ?` 中提取表 `users`、字段 `id`、占位符 `?` |
| 3 | 格式生成 | 按用户指定的输出格式（文件类型/字段结构）生成包装代码或文本源 | 生成 Python 的 MySQL 连接包装类，或生成 Markdown 格式的查询说明文档 |
| 4 | 置信度标注 | 对识别结果和生成内容标注置信度等级（高/中/低） | 字段映射关系明确时标注 `[置信度:高]`，存在歧义时标注 `[置信度:中]` |
| 5 | 批量与自定义 | 支持一次处理多个查询/文件，并允许用户自定义输出模板 | 传入 10 个 SQL 文件，按自定义的 Java 模板批量生成 DAO 代码 |

### 不能做（明确边界）

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行 SQL | 本技能仅生成代码/文本，不连接数据库执行查询 |
| 2 | 不优化查询性能 | 不分析执行计划，不提供索引建议（除非用户明确要求且提供 EXPLAIN 结果） |
| 3 | 不处理非 MySQL 方言 | 仅支持 MySQL 语法，不兼容 PostgreSQL、SQL Server 等方言 |
| 4 | 不保证生成代码可编译 | 生成代码依赖目标语言环境，用户需自行验证编译与运行 |
| 5 | 不处理二进制文件 | 仅支持文本格式输入（.sql、.txt、.md、.json、.csv 等） |

### 适用对象

- 需要为 MySQL 查询生成 Python/Java/Go/Node.js 等语言包装代码的开发者
- 需要将 SQL 查询转换为文档、测试用例、API 接口说明的团队
- 需要批量处理多个 SQL 文件并统一输出格式的数据工程师
- 需要快速生成数据库操作模板的初级开发者


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

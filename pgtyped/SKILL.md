---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: pgtyped
name: pgtyped
displayName: SQL类型安全 查询生成 代码转换
description: 将SQL查询转换为类型安全的TypeScript代码，提升开发效率与可靠性。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/pgtyped
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["pgtyped", "SQL类型安全", "TypeScript查询", "pgTyped", "类型化SQL", "数据库类型生成"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# pgTyped — SQL 类型安全转换 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做（核心能力）

| 编号 | 能力项 | 说明 | 输入示例 | 输出示例 |
|------|--------|------|----------|----------|
| C1 | SQL 查询转类型化 TS 代码 | 将原始 SQL 语句转换为带类型定义的 TypeScript 查询函数 | `SELECT id, name FROM users WHERE id = $1` | 生成 `IUser` 接口 + `findUserById` 函数 |
| C2 | 类型定义自动推导 | 根据 SQL 结果集结构自动生成 TypeScript 接口/类型别名 | `SELECT u.id, u.email, p.title FROM users u JOIN posts p ON ...` | 生成 `IUserWithPost` 联合类型 |
| C3 | 参数类型标注 | 识别 SQL 中的占位符（`$1`, `$2`）并映射为函数参数类型 | `INSERT INTO products (name, price) VALUES ($1, $2)` | 生成 `(name: string, price: number) => ...` |
| C4 | 批量查询处理 | 支持一次处理多个 SQL 查询语句，分别生成对应代码 | 包含 3 条 SQL 的 `.sql` 文件 | 生成 3 个独立查询模块 |
| C5 | 配置与自检 | 提供 `--selftest` 自检模式和 `--version` 版本查询 | 命令行执行 `pgtyped --selftest` | 输出环境自检报告 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行 SQL | 仅做静态分析和代码生成，不连接数据库执行查询 |
| L2 | 不处理动态 SQL | 不支持字符串拼接、条件动态构建的 SQL 片段 |
| L3 | 不识别存储过程 | 仅处理标准 DQL/DML 语句，不解析 PL/pgSQL 等过程化语言 |
| L4 | 不保证运行时性能 | 生成的代码类型安全，但查询效率取决于数据库自身优化 |
| L5 | 不支持非 PostgreSQL 方言 | 仅兼容 PostgreSQL 语法特性（如 `::type` 转换、`RETURNING` 子句） |

### 1.3 适用对象

- **前端/全栈开发者**：希望在 TypeScript 项目中获得数据库查询的类型安全保障
- **后端服务开发者**：需要将现有 SQL 迁移到类型化查询层
- **技术负责人**：评估在团队中引入类型安全 SQL 方案的可行性


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: dbgo
name: dbgo
displayName: 数据库消费包 代码生成 查询优化
description: 根据数据库与领域模型，自动生成含优化Go代码与SQL的消费包。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/dbgo
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: skill_forge_lab
agent_created: true
trigger_words: ["dbgo", "数据库消费包", "SQL生成", "Go代码生成", "查询优化", "数据访问层"]
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

# dbgo — 数据库消费包生成器

## 一、能力边界速查卡

本 Skill 面向需要快速搭建数据访问层的开发者，将数据库结构描述与领域模型定义转化为可直接编译的 Go 代码与 SQL 查询文件。

| 维度 | 说明 |
|------|------|
| **输入** | 数据库 Schema（DDL 或 JSON 描述）、领域模型定义（Go struct 或 JSON）、查询需求描述 |
| **输出** | 一个完整的数据库消费包目录，包含 `*.go` 源文件、`*.sql` 查询文件、`go.mod` 依赖声明 |
| **核心能力** | ① 表结构解析与模型映射 ② CRUD 操作代码生成 ③ 查询 SQL 自动优化（索引建议、JOIN 简化） ④ 批量操作支持 ⑤ 事务封装 |
| **不能做** | ① 无法连接真实数据库执行验证 ② 不处理数据库迁移（Migration）脚本 ③ 不生成测试用例 ④ 不保证生成代码在特定版本下的编译通过（需用户自行验证） |
| **适用对象** | 使用 Go 语言开发、依赖 SQL 关系型数据库（MySQL/PostgreSQL/SQLite）的中级及以上开发者 |

**输入限制说明**：Schema 描述需遵循标准 DDL 语法或 JSON 字段映射规则；领域模型需包含字段类型标签（如 `json:"user_id"`）。若输入缺失关键字段类型，将按 `[需核实:字段类型]` 占位处理。


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

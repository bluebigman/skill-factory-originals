---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: sql-code-generator
name: sql-code-generator
displayName: 数据库查询 SQL 语句生成
description: 将自然语言需求转化为规范SQL语句，辅助数据库查询与学习。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/sql-code-generator
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Studio
agent_created: true
trigger_words: ["SQL查询", "sql code generator", "数据库查询", "写SQL", "生成查询语句", "查数据", "编写查询"]
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

# SQL 代码生成器 Skill 文档

## 一、能力边界（速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 自然语言转 SQL | 将中文描述转换为标准 SQL 语句 | "查所有年龄大于30的用户" → `SELECT * FROM users WHERE age > 30;` |
| 多表关联查询 | 支持 JOIN 操作生成 | "查每个部门的员工数量" → 生成含 GROUP BY 的 JOIN 语句 |
| 聚合函数应用 | 支持 COUNT/SUM/AVG/MAX/MIN | "统计订单总金额" → `SELECT SUM(amount) FROM orders;` |
| 条件过滤优化 | 生成 WHERE 子句及逻辑组合 | "查北京或上海的用户" → `WHERE city IN ('北京','上海')` |
| 排序与分页 | 生成 ORDER BY 和 LIMIT 子句 | "按时间倒序取前10条" → `ORDER BY created_at DESC LIMIT 10;` |
| 子查询生成 | 支持嵌套查询场景 | "查工资高于平均工资的员工" → 生成含子查询的语句 |
| 学习辅助 | 为每条 SQL 附注释说明 | 每条语句附带关键语法点注释 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行 SQL | 仅生成语句，不连接数据库执行 |
| 不优化索引 | 不提供物理存储层面的调优建议 |
| 不处理非关系型数据库 | 仅支持 SQL 标准语法（MySQL/PostgreSQL/SQLite 为主） |
| 不生成 DDL/DML 之外的语句 | 不生成 GRANT、REVOKE 等权限管理语句 |
| 不保证语法完全兼容 | 不同数据库方言存在差异，需自行验证 |

### 1.3 适用对象

- 数据分析师：快速获取查询语句原型
- 后端开发人员：减少编写基础 SQL 的时间
- 数据库初学者：通过自然语言对照学习 SQL 语法
- 产品经理：验证数据可行性，与开发沟通更高效


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

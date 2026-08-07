---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: spiral
name: spiral
displayName: 数据库管理 ERD可视化 跨库客户端
description: 跨平台数据库客户端，支持SQL与NoSQL管理及ERD可视化操作。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/spiral
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingDataWorks
agent_created: true
trigger_words: ["spiral", "数据库客户端", "ERD可视化", "SQL管理", "NoSQL管理", "数据建模", "表结构设计"]
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

# spiral — 跨平台数据库客户端与 ERD 可视化操作指南

## 1. 能力边界（一页纸速查卡）

### 1.1 能做

| 能力项 | 说明 | 典型场景 |
|--------|------|----------|
| 多数据库连接 | 支持主流 SQL（MySQL、PostgreSQL、SQLite、SQL Server）与 NoSQL（MongoDB、Redis） | 同时管理开发库与生产库 |
| SQL 编辑与执行 | 语法高亮、多语句执行、执行计划查看 | 编写复杂联表查询 |
| NoSQL 数据操作 | 文档增删改查、集合/索引管理 | 调整 MongoDB 文档结构 |
| ERD 可视化 | 自动生成实体关系图，支持拖拽布局与导出 | 向团队展示表间外键关系 |
| 数据导出导入 | CSV、JSON、SQL 脚本格式 | 迁移测试数据到新环境 |
| 连接配置管理 | 加密保存连接串，支持环境分组 | 区分 dev/staging/prod 配置 |

### 1.2 不能做

- 不提供数据库性能调优建议（如索引优化策略）
- 不替代数据库备份工具（仅提供导出功能）
- 不支持分布式事务协调
- 不包含数据脱敏或合规审计功能
- 不提供跨数据库的实时数据同步

### 1.3 适用对象

- 后端开发人员：日常 SQL 调试与表结构设计
- 数据工程师：快速查看数据血缘与表关联
- 技术负责人：通过 ERD 评审数据库设计
- 运维人员：多环境连接配置管理


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: spiral
name: spiral
displayName: 数据库客户端 跨平台管理 ERD可视化
description: 跨平台数据库客户端，支持SQL与NoSQL管理及ERD可视化操作。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/spiral
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataFlow Studio
agent_created: true
trigger_words: ["spiral", "数据库客户端", "ERD可视化", "SQL管理", "NoSQL管理"]
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

## 一、能力边界（一页纸速查卡）

### 1.1 核心能力清单

| 序号 | 能力项 | 说明 | 适用场景 |
|------|--------|------|----------|
| 1 | 多类型数据库连接 | 支持 SQL（MySQL/PostgreSQL/SQLite 等）与 NoSQL（MongoDB/Redis 等） | 日常开发、测试环境管理 |
| 2 | 交互式 ERD 可视化 | 将表结构、字段关系以实体-关系图呈现 | 数据库设计评审、文档输出 |
| 3 | 查询执行与结果导出 | 执行 SQL 查询，结果可导出为 CSV/JSON | 数据分析、报表生成 |
| 4 | 批量操作支持 | 多表批量更新、删除、结构同步 | 版本升级、数据清洗 |
| 5 | 自定义格式输出 | 按用户指定字段结构生成结果 | 接口对接、数据迁移 |

### 1.2 能力边界声明

**能做：**
- 解析用户提供的数据库连接串、SQL 文件、ERD 描述文本
- 识别表名、字段名、数据类型、主外键关系
- 按约定格式输出结构化结果（JSON/CSV/Markdown 表格）
- 对不确定项标注置信度提示

**不能做：**
- 无法直接连接真实数据库执行操作（需用户提供连接信息）
- 无法自动推断缺失的表结构或字段类型
- 无法处理加密数据库文件或私有协议
- 不提供数据备份或恢复功能

**适用对象：**
- 数据库管理员（DBA）
- 后端开发工程师
- 数据分析师
- 系统架构师


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

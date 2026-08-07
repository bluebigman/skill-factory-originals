---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: sqlgen
name: sqlgen
displayName: 数据转换 SQL 查询生成器
description: 将用户数据文件转换为结构化结果，生成 SQL 查询语句。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/sqlgen
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Studio
agent_created: true
trigger_words: ["SQL查询", "数据转换", "查询生成", "sqlgen", "结构化输出"]
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

# sqlgen — 数据转换与 SQL 查询生成 Skill

## 一、能力边界速查卡

### 1.1 能做什么

| 序号 | 能力项 | 说明 | 输入示例 | 输出示例 |
|------|--------|------|----------|----------|
| 1 | 数据/文件/URL 转结构化结果 | 解析 CSV、JSON、TXT 或网页表格，提取关键字段 | `users.csv` 含 id,name,email | 结构化行记录列表 |
| 2 | 关键信息识别与保留 | 自动识别主键、外键、枚举值、时间戳等特征 | 数据中重复出现的 `user_id` 字段 | 字段类型标注 + 保留原始值 |
| 3 | 按约定格式生成输出 | 支持 JSON、Markdown 表格、SQL INSERT 语句三种输出 | `--format sql` 参数 | 可执行的 SQL 语句块 |
| 4 | 置信度标注 | 对推断字段类型、模糊匹配结果给出 0~1 置信度 | 无法确定 `status` 字段取值范围 | `[置信度:0.82] status TEXT` |
| 5 | 批量处理与自定义格式 | 支持多文件循环处理、自定义分隔符与模板 | 10 个 CSV 文件 + 自定义模板 | 按模板渲染的批量结果 |

### 1.2 不能做什么

- 不能直接连接数据库执行 SQL（仅生成语句，不负责运行）
- 不能理解自然语言业务语义（如"找出所有 VIP 用户"需先明确 VIP 定义）
- 不能处理加密文件或需要身份认证的 URL
- 不能保证生成 SQL 与特定数据库方言完全兼容（默认 ANSI SQL，方言需显式指定）

### 1.3 适用对象

- 需要快速将数据文件转为 SQL 查询语句的开发者
- 需要批量清洗并结构化数据的运维/数据分析人员
- 需要在 C++20 项目中嵌入轻量 ORM 逻辑的工程师


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

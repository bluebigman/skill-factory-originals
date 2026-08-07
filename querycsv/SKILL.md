---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: querycsv
name: querycsv
displayName: CSV数据查询 SQL分析 表格处理
description: 加载CSV文件并用SQL查询分析，支持导出结果。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/querycsv
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataFlow Studio
agent_created: true
trigger_words: ["SQL查询", "CSV查询", "表格分析", "数据筛选", "csv转sql"]
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

# QueryCSV — CSV 数据 SQL 查询与导出工具

## 一、能力边界速查卡

### 1.1 能做什么

| 编号 | 能力项 | 说明 |
|------|--------|------|
| C1 | CSV 文件加载 | 支持本地文件路径、URL 链接、粘贴文本三种输入方式 |
| C2 | SQL 查询执行 | 对已加载的 CSV 数据执行 SELECT、WHERE、GROUP BY、ORDER BY、JOIN 等标准 SQL 操作 |
| C3 | 结果导出 | 查询结果可导出为 CSV、JSON、Markdown 表格三种格式 |
| C4 | 字段类型推断 | 自动识别数值、日期、字符串等字段类型，并在查询时按类型处理 |
| C5 | 批量操作 | 支持一次加载多个 CSV 文件，通过表别名进行关联查询 |

### 1.2 不能做什么

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不支持写入原文件 | 所有操作均为只读，不会修改原始 CSV 文件 |
| L2 | 不支持 INSERT/UPDATE/DELETE | 仅支持查询类 SQL 语句，不支持数据变更操作 |
| L3 | 不支持跨数据库 JOIN | 仅能关联已加载的 CSV 文件，无法连接外部数据库 |
| L4 | 大文件性能受限 | 单文件超过 200MB 时查询响应时间可能显著增加 |
| L5 | 不支持复杂窗口函数 | 仅支持基础聚合函数（SUM/AVG/COUNT/MAX/MIN） |

### 1.3 适用对象

- 需要快速分析 CSV 数据但不想写 Python/Pandas 代码的数据分析师
- 需要验证 CSV 数据质量的数据工程师
- 需要从 CSV 中提取特定信息并生成报表的业务人员
- 需要在命令行环境中进行数据探索的开发者


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

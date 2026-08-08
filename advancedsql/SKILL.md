---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: advancedsql
name: advancedsql
displayName: SQL查询构建 数据连接 结果映射
description: 将自然语言或数据文件转换为结构化SQL查询与结果集。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/advancedsql
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinQuery Architect
agent_created: true
trigger_words: ["advancedsql", "SQL查询构建", "数据库连接", "查询生成器", "SQL映射", "数据查询转换"]
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

# AdvancedSQL 技能文档

## 一、能力边界速查卡

本技能面向需要将非结构化输入（自然语言描述、CSV 文件、URL 指向的数据源）转化为可执行 SQL 查询及结构化结果集的开发者与数据分析师。

### 1.1 能处理的任务

| 编号 | 任务类型 | 输入示例 | 输出示例 |
|------|----------|----------|----------|
| T1 | 自然语言转 SQL | "找出上月订单金额超过 5000 的客户名单" | `SELECT customer_id, SUM(amount) FROM orders WHERE order_date >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH) GROUP BY customer_id HAVING SUM(amount) > 5000;` |
| T2 | 数据文件结构识别 | 包含 `id,name,amount` 三列的 CSV 文件 | 字段类型推断 + 建表语句 |
| T3 | URL 数据源解析 | 指向公开数据集的 URL | 数据预览 + 查询建议 |
| T4 | 查询结果格式化 | 原始 SQL 执行结果 | JSON / Markdown 表格 / 键值对列表 |
| T5 | 批量查询转换 | 多条自然语言查询列表 | 对应的 SQL 语句集合 |

### 1.2 不能处理的任务

| 编号 | 限制说明 |
|------|----------|
| L1 | 不执行实际数据库连接，仅生成查询语句与结果映射方案 |
| L2 | 不处理二进制文件（图片、音频中的隐含数据） |
| L3 | 不进行数据清洗，仅做结构识别与映射 |
| L4 | 不生成针对特定数据库方言的优化提示（如索引建议） |
| L5 | 不处理需要身份认证的私有数据源 |

### 1.3 适用对象

- 需要快速将业务需求转化为 SQL 的初级开发者
- 需要批量处理查询模板的数据分析师
- 需要将外部数据文件快速导入数据库的运维人员


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

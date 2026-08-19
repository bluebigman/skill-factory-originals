---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: advancedsql
name: advancedsql
displayName: 数据查询 SQL 方言适配 结果集生成
description: 将自然语言或数据文件转换为结构化 SQL 查询与结果集，支持多方言适配与优化建议。
version: 2.0.1
rules_version: cpr-20260819-n551
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/advancedsql
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: QueryForge Studio
agent_created: true
trigger_words: ["advancedsql", "SQL生成", "自然语言转SQL", "方言适配", "查询优化", "数据文件转SQL"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# AdvancedSQL 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|--------|----------|
| 输入处理 | 自然语言描述、CSV/JSON/Excel 文件、已有 SQL 片段 | 二进制数据文件、加密数据库文件 |
| SQL 生成 | SELECT/JOIN/GROUP BY/窗口函数/子查询/CTE | 数据库管理命令（GRANT/REVOKE）、DDL 自动执行 |
| 方言适配 | MySQL、PostgreSQL、SQLite、SQL Server、Oracle、BigQuery | 非关系型查询语言（MongoDB Aggregation、Elasticsearch DSL） |
| 结果输出 | 结构化结果集（JSON/CSV 格式）、执行计划解读 | 直接连接数据库执行（需用户自行执行） |
| 优化建议 | 索引建议、查询重写、执行计划分析 | 自动索引创建、自动性能调优 |

### 1.2 适用对象

- **数据分析师**：快速将业务问题转化为可执行 SQL
- **后端开发者**：需要多数据库方言适配的查询逻辑
- **数据产品经理**：验证数据需求的可实现性
- **运维工程师**：排查慢查询并获取优化方向

### 1.3 输入限制

- 自然语言描述不超过 500 字
- 数据文件大小不超过 10MB
- 单次生成的 SQL 语句不超过 200 行
- 方言适配最多同时指定 3 种目标方言

---

## 二、触发方式

### 2.1 触发词

直接使用 `advancedsql` 或以下同义场景词触发：

| 场景词 | 示例用法 |
|--------|----------|
| SQL生成 | "帮我生成一个查询最近30天订单的SQL" |
| 自然语言转SQL | "把'统计各部门平均薪资'转成SQL" |
| 方言适配 | "把这个查询改成PostgreSQL语法" |
| 查询优化 | "这个SQL太慢了，帮我优化一下" |
| 数据文件转SQL | "根据这个CSV文件生成建表语句和查询" |

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 触发动作 |
|-----------------|---------|---------|
| "我有一堆数据想查一下" | 从数据文件提取信息 | 解析文件 → 生成建表语句 → 生成查询 |
| "这个查询在MySQL能跑，Oracle不行" | 方言转换 | 识别源方言 → 转换目标方言 → 输出兼容代码 |
| "报表要按周汇总，怎么写" | 时间维度聚合 | 生成 GROUP BY 周粒度的查询 |
| "两个表关联后数据变多了" | JOIN 逻辑问题 | 检查关联条件 → 提供去重方案 |
| "这个SQL跑了10分钟" | 性能问题 | 分析执行计划 → 给出优化建议 |

---

## 三、标准流程

### 3.1 前置条件

- 用户需明确提供：数据源类型（文件/描述/已有SQL）
- 若为文件输入，需确认文件格式（CSV/JSON/Excel）及编码
- 若需方言适配，需指定源方言和目标方言
- 若需优化建议，需提供执行计划或表结构信息

### 3.2 执行步骤

**步骤 1：需求解析（输入阶段）**

| 输入类型 | 解析动作 | 输出中间产物 |
|---------|---------|-------------|
| 自然语言 | 提取实体（表名、字段、条件、聚合方式） | 结构化查询意图 |
| 数据文件 | 识别列类型、推断主键、检测数据分布 | 表结构定义草案 |
| 已有SQL | 语法解析、方言识别、逻辑拆解 | AST 抽象语法树 |

**步骤 2：SQL 生成（转换阶段）**

1. 根据查询意图构建逻辑查询计划
2. 映射到目标方言的语法规则
3. 生成带注释的 SQL 代码
4. 标注潜在风险点（如全表扫描、隐式类型转换）

**步骤 3：结果集构造（输出阶段）**

- 若输入为数据文件：模拟执行并返回前 100 行结果
- 若输入为自然语言：返回 SQL 及预期结果结构说明
- 若输入为已有 SQL：返回优化后的 SQL 及对比说明

**步骤 4：优化建议（增值阶段）**

- 索引建议：基于 WHERE/JOIN 条件推荐复合索引
- 查询重写：将子查询改为 JOIN、避免 SELECT *
- 执行策略：建议分区、分页、缓存等策略

### 3.3 输出规范

```json
{
  "status": "success",
  "sql": "SELECT ...",
  "dialect": "mysql",
  "result_preview": [{"column": "value"}],
  "optimization_tips": ["建议在 user_id 上建立索引"],
  "risk_warnings": ["该查询涉及全表扫描，数据量超过100万行时建议添加WHERE条件"]
}
```

---

## 四、置信度门控

### 4.1 信息不足处理

当输入信息不足以生成准确 SQL 时，使用 `[需核实:字段]` 占位，不编造：

| 场景 | 占位示例 | 用户需补充 |
|------|---------|-----------|
| 表名不明确 | `SELECT * FROM [需核实:表名]` | 实际表名 |
| 字段名模糊 | `WHERE [需核实:日期字段] > '2024-01-01'` | 具体字段名 |
| 关联条件缺失 | `JOIN orders ON [需核实:关联字段]` | 两表关联键 |
| 聚合粒度不明 | `GROUP BY [需核实:分组维度]` | 按什么维度分组 |

### 4.2 置信度分级

| 置信度 | 判定标准 | 输出策略 |
|--------|---------|---------|
| 高（≥90%） | 所有表名、字段、条件明确 | 直接输出完整 SQL |
| 中（70-89%） | 部分字段需推断 | 输出 SQL + 标注推断字段 |
| 低（<70%） | 关键信息缺失 | 输出占位符 + 引导用户补充 |

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|---------|---------|---------|
| ASQL-001 | 无法识别的文件格式 | "该文件格式暂不支持，请提供 CSV、JSON 或 Excel 文件" | 转换文件格式后重试 |
| ASQL-002 | 自然语言描述过于模糊 | "描述中缺少关键查询条件，请补充表名、筛选条件或聚合方式" | 按模板重新描述：查询[表]中[字段]，按[条件]筛选，按[维度]聚合 |
| ASQL-003 | 方言转换失败 | "目标方言不支持该语法特性，已保留源语法并标注" | 检查目标方言版本，或简化查询逻辑 |
| ASQL-004 | 数据文件列类型推断失败 | "无法自动识别[列名]的数据类型，请手动指定" | 提供列类型映射，如 `date_col: DATE` |
| ASQL-005 | SQL 语法错误 | "生成的 SQL 存在语法问题，已标记错误位置" | 根据错误位置修正表名或字段名 |
| ASQL-006 | 优化建议生成失败 | "无法生成优化建议，请提供执行计划或表结构信息" | 执行 `EXPLAIN` 并粘贴结果 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 坑 | 反模式（错误做法） | 正确做法 |
|----|-------------------|---------|
| 忽略方言差异 | 直接复制 MySQL 的 `LIMIT` 到 SQL Server | 使用 `TOP` 或 `OFFSET FETCH` 适配语法 |
| 过度依赖 AI 生成 | 不检查生成的 SQL 直接执行 | 先审查 WHERE 条件和 JOIN 逻辑 |
| 忽略数据量级 | 对亿级表不加 WHERE 条件 | 强制添加时间范围或分页限制 |
| 混淆字段类型 | 对字符串字段使用数值比较 | 确认字段类型后使用正确的比较操作符 |
| 忽视 NULL 处理 | 使用 `= NULL` 而非 `IS NULL` | 明确 NULL 语义，使用 `IS NULL` 或 `COALESCE` |

### 6.2 反模式示例

**反模式 1：无脑使用 SELECT ***

```sql
-- ❌ 错误
SELECT * FROM orders WHERE customer_id = 123;

-- ✅ 正确
SELECT order_id, order_date, total_amount 
FROM orders 
WHERE customer_id = 123;
```

**反模式 2：忽略时区问题**

```sql
-- ❌ 错误（直接比较日期字符串）
WHERE create_time >= '2024-01-01'

-- ✅ 正确（显式转换时区）
WHERE create_time >= TIMESTAMP '2024-01-01 00:00:00' AT TIME ZONE 'Asia/Shanghai'
```

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
输入 → 输出 流程：
1. 说清需求：表名 + 字段 + 条件 + 聚合
2. 指定方言：MySQL / PG / SQLite / SQL Server / Oracle / BigQuery
3. 获取结果：SQL + 预览 + 优化建议
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」了解适用范围
2. 使用「触发方式」中的示例模板描述需求
3. 检查输出中的 `risk_warnings` 字段
4. 在测试环境执行生成的 SQL

### 7.3 进阶路径（熟练用户）

1. 利用「方言适配」进行跨数据库迁移
2. 结合「优化建议」重构慢查询
3. 使用「置信度门控」处理复杂业务场景
4. 参考「错误码体系」快速定位问题

### 7.4 专家路径（深度定制）

- 自定义方言模板：在配置文件中添加新的方言规则
- 扩展文件解析器：支持 Parquet、Avro 等格式
- 集成执行计划分析：对接 EXPLAIN 输出进行深度优化

---

## 八、参数配置参考

### 8.1 方言支持矩阵

| 方言 | 分页语法 | 字符串拼接 | 日期函数 | 窗口函数 |
|------|---------|-----------|---------|---------|
| MySQL | LIMIT/OFFSET | CONCAT() | DATE_FORMAT() | 8.0+ 支持 |
| PostgreSQL | LIMIT/OFFSET | \|\| | TO_CHAR() | 完整支持 |
| SQLite | LIMIT/OFFSET | \|\| | DATE() | 3.25+ 支持 |
| SQL Server | OFFSET/FETCH | + | FORMAT() | 完整支持 |
| Oracle | ROWNUM/OFFSET | \|\| | TO_CHAR() | 完整支持 |
| BigQuery | LIMIT/OFFSET | CONCAT() | FORMAT_DATE() | 完整支持 |

### 8.2 文件解析规则

| 文件类型 | 支持扩展名 | 编码要求 | 大小限制 |
|---------|-----------|---------|---------|
| CSV | .csv | UTF-8/GBK | 10MB |
| JSON | .json | UTF-8 | 10MB |
| Excel | .xlsx/.xls | - | 10MB |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用须知：**

1. 本 Skill 生成的 SQL 代码仅供学习和参考，使用者需自行验证其在目标环境中的正确性和安全性。
2. 使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于数据丢失、系统故障、业务损失等。
3. 禁止对本 Skill 进行反向工程、反编译、破解或试图提取底层算法。
4. 本 Skill 不提供任何形式的明示或暗示担保，包括但不限于适销性、特定用途适用性和非侵权保证。
5. 使用者应遵守相关法律法规，不得将本 Skill 用于非法目的。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 QueryForge Studio

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## 附录：版本信息

- **版本号**：1.0.0
- **更新日期**：2024-01-15
- **变更记录**：
  - 初始版本发布
  - 支持 6 种主流 SQL 方言
  - 内置 6 个错误码处理机制
  - 提供 3 层渐进式学习路径

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并验证输出结果。*

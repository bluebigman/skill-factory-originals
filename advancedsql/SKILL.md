---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: advancedsql
name: advancedsql
displayName: 数据查询 SQL 转换 结果集生成
description: 将自然语言或数据文件转换为结构化 SQL 查询与结果集。
version: 1.0.2
rules_version: cpr-20260811-n351
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/advancedsql
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["advancedsql", "SQL查询构建", "数据库连接", "查询生成器", "SQL映射", "自然语言转SQL", "表结构转查询"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# AdvancedSQL 技能文档

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 能力项 | 说明 | 输入示例 | 输出示例 |
|--------|------|----------|----------|
| 自然语言转 SQL | 将中文/英文描述转换为标准 SQL 语句 | "查询最近7天订单金额大于1000的客户" | `SELECT * FROM orders WHERE order_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) AND amount > 1000;` |
| 数据文件结构识别 | 读取 CSV/JSON/Excel 文件，推断表结构并生成建表语句 | `customers.csv`（含 id,name,email 列） | `CREATE TABLE customers (id INT, name VARCHAR(255), email VARCHAR(255));` |
| 查询结果集生成 | 根据 SQL 语句和模拟数据，生成结果集预览 | `SELECT * FROM users WHERE age > 30;` | 返回符合条件的数据行（模拟或真实） |
| SQL 优化建议 | 对已有 SQL 提供索引、写法优化建议 | 慢查询日志中的 SQL | 优化建议列表（含索引建议、改写方案） |
| 多方言适配 | 支持 MySQL、PostgreSQL、SQLite、SQL Server 语法转换 | MySQL 语法 SQL | 转换为 PostgreSQL 语法 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行真实数据库操作 | 本技能不直接连接生产数据库执行 DML/DDL，仅生成语句和模拟结果 |
| 不处理非结构化数据 | 图片、音频、视频中的信息无法直接转换为 SQL |
| 不保证 SQL 语义正确性 | 生成的 SQL 基于输入推断，业务逻辑需人工复核 |
| 不处理敏感数据 | 输入数据文件中的密码、密钥等敏感字段会被脱敏提示 |
| 不支持复杂窗口函数推导 | 涉及多级子查询、递归 CTE 等场景需人工确认逻辑 |

### 1.3 适用对象

- **数据分析师**：快速将业务问题转化为可执行的 SQL 查询
- **后端开发人员**：在开发环境中生成建表语句和基础 CRUD 操作
- **产品经理**：理解数据表结构，验证数据需求可行性
- **运维人员**：生成监控查询语句，排查数据异常

---

## 二、触发方式：场景映射表

| 触发词/场景 | 用户意图 | 技能响应 |
|-------------|----------|----------|
| "帮我写个 SQL 查一下..." | 自然语言转 SQL | 解析描述，生成 SQL 语句 |
| "这个 CSV 怎么导入数据库？" | 文件结构识别 | 读取文件头，生成建表语句和导入建议 |
| "这条 SQL 能不能优化？" | SQL 优化 | 分析执行计划，给出优化建议 |
| "把这段 MySQL 转成 PG 语法" | 方言转换 | 语法转换并标注差异点 |
| "模拟一下这个查询的结果" | 结果集生成 | 根据表结构和条件生成模拟数据 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 缺失处理 |
|------|------|----------|
| 输入内容 | 自然语言描述 / 数据文件路径 / SQL 语句 | 提示用户补充输入 |
| 数据库方言 | 明确指定（MySQL/PostgreSQL/SQLite/SQL Server） | 默认 MySQL，提示可切换 |
| 表结构信息 | 有明确的表名和字段名 | 若缺失，使用占位符 `[需核实:表名]` |

### 3.2 执行步骤

**步骤 1：输入解析**
- 接收用户输入，识别类型（文本/SQL/文件路径）
- 提取关键实体：表名、字段、条件、聚合函数、排序要求

**步骤 2：语义映射**
- 将自然语言中的业务术语映射为 SQL 关键字
- 示例映射表：

| 自然语言 | SQL 映射 |
|----------|----------|
| "大于" / "超过" | `>` |
| "最近 N 天" | `DATE_SUB(CURDATE(), INTERVAL N DAY)` |
| "每个" / "按...分组" | `GROUP BY` |
| "前 N 个" | `LIMIT N` |

**步骤 3：SQL 生成**
- 按 SQL 标准语法组装语句
- 添加注释说明每个子句的业务含义

**步骤 4：结果集模拟**
- 若用户需要结果预览，根据表结构和条件生成 3-5 行模拟数据
- 模拟数据标注"模拟数据，非真实查询结果"

**步骤 5：输出与建议**
- 输出完整 SQL 语句、模拟结果、使用注意事项
- 提供下一步建议（如"是否需要转换为其他方言？"）

### 3.3 输出规范

```json
{
  "status": "success",
  "sql": "SELECT ...",
  "dialect": "mysql",
  "result_preview": [
    {"id": 1, "name": "张三", "amount": 1500.00}
  ],
  "notes": ["该查询使用了索引 idx_orders_amount，建议确认索引存在"],
  "next_steps": ["转换为 PostgreSQL 语法", "生成建表语句"]
}
```

---

## 四、置信度门控

当输入信息不足以生成准确 SQL 时，使用以下占位符，**不编造**：

| 场景 | 占位符示例 | 处理方式 |
|------|------------|----------|
| 表名未知 | `[需核实:表名]` | 提示用户提供表名 |
| 字段名未知 | `[需核实:字段名]` | 提示用户提供字段列表 |
| 条件模糊 | `[需核实:筛选条件]` | 询问用户具体条件 |
| 方言未指定 | `[需核实:数据库类型]` | 默认 MySQL，提示确认 |

**示例**：
用户输入："查一下所有用户的订单"
输出：
```sql
SELECT * FROM [需核实:用户表名] u
JOIN [需核实:订单表名] o ON u.id = o.user_id;
```
提示："请提供用户表和订单表的实际表名，以便生成完整查询。"

---

## 五、错误码体系

| 错误码 | 错误场景 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 输入为空 | "未检测到有效输入，请提供自然语言描述、SQL 语句或文件路径。" | 重新输入内容 |
| E002 | 文件格式不支持 | "仅支持 CSV、JSON、Excel（.xlsx）格式，当前文件无法解析。" | 转换文件格式后重试 |
| E003 | SQL 语法错误 | "生成的 SQL 存在语法错误，请检查表名和字段名是否正确。" | 核对表结构，修正字段名 |
| E004 | 方言转换失败 | "当前方言转换规则不支持该语法，请手动调整。" | 参考方言差异文档手动修改 |
| E005 | 模拟数据生成失败 | "无法根据当前表结构生成模拟数据，请补充字段类型信息。" | 提供字段类型定义 |
| E006 | 敏感信息检测 | "输入内容包含疑似敏感字段（如密码、密钥），已自动脱敏处理。" | 确认脱敏后继续 |

---

## 六、FAQ 反模式对照

### 反模式 1：忽略表结构直接生成
- **错误做法**：用户只说"查订单"，直接生成 `SELECT * FROM orders`
- **正确做法**：询问订单表的关键字段，确认查询范围
- **反模式示例**：
  - ❌ "SELECT * FROM orders;"
  - ✅ "SELECT order_id, customer_name, order_date, total_amount FROM orders WHERE order_date >= '2024-01-01';"

### 反模式 2：过度依赖默认方言
- **错误做法**：所有 SQL 都按 MySQL 语法生成
- **正确做法**：确认目标数据库类型，按方言生成
- **反模式示例**：
  - ❌ 使用 `LIMIT` 生成 SQL Server 查询
  - ✅ 使用 `SELECT TOP 10` 生成 SQL Server 查询

### 反模式 3：模拟数据误导
- **错误做法**：模拟数据未标注，用户误以为是真实数据
- **正确做法**：明确标注"模拟数据"，并提示仅用于结构验证
- **反模式示例**：
  - ❌ 直接返回模拟数据行
  - ✅ 返回数据前添加提示："以下为模拟数据，非真实查询结果"

### 反模式 4：忽略索引优化
- **错误做法**：生成 SQL 时不考虑索引使用
- **正确做法**：在 SQL 注释中标注建议索引
- **反模式示例**：
  - ❌ `SELECT * FROM orders WHERE customer_id = 123;`（无索引提示）
  - ✅ `SELECT * FROM orders WHERE customer_id = 123; -- 建议在 customer_id 上创建索引`

### 反模式 5：不处理空值
- **错误做法**：生成的 SQL 未考虑 NULL 值处理
- **正确做法**：在条件中添加 `IS NOT NULL` 或使用 `COALESCE`
- **反模式示例**：
  - ❌ `SELECT * FROM users WHERE email = '';`
  - ✅ `SELECT * FROM users WHERE email IS NOT NULL AND email != '';`

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
输入 → 输出
"查用户表所有数据" → SELECT * FROM users;
"CSV 转建表" → 读取文件头生成 CREATE TABLE
"SQL 优化" → 分析并给出建议
"MySQL 转 PG" → 语法转换
```

### 7.2 新手路径（5 分钟）

1. 阅读「能力边界」了解适用范围
2. 使用「触发方式」中的示例输入进行测试
3. 查看「标准流程」理解处理逻辑
4. 遇到问题参考「错误码体系」

### 7.3 进阶路径（15 分钟）

1. 深入理解「置信度门控」机制，学会提供完整信息
2. 掌握「FAQ 反模式」中的正确做法
3. 尝试多方言转换和复杂查询生成
4. 结合「SQL 优化建议」功能提升查询性能

---

## 八、参数配置表

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `dialect` | string | `mysql` | 目标数据库方言 |
| `include_preview` | boolean | `true` | 是否生成模拟结果集 |
| `max_preview_rows` | integer | `5` | 模拟结果最大行数 |
| `sensitive_detection` | boolean | `true` | 是否启用敏感字段检测 |
| `comment_level` | string | `normal` | SQL 注释详细程度（minimal/normal/detailed） |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 生成的 SQL 语句、模拟数据及建议仅供参考，不构成任何形式的保证或承诺。

2. **禁止反向工程**：未经授权，不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码。

3. **数据安全**：使用者应确保输入数据不包含敏感信息。若输入包含敏感数据，本 Skill 会进行脱敏处理，但使用者仍需自行承担数据泄露风险。

4. **合规使用**：使用者应遵守所在国家/地区的法律法规，不得将本 Skill 用于非法用途。

5. **免责声明**：本 Skill 按"现状"提供，不提供任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权性。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 LinguaForge

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

## 十一、版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0.0 | 2024-01-15 | 初始版本，包含核心功能：自然语言转 SQL、文件结构识别、结果集模拟、方言转换、优化建议 |

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*

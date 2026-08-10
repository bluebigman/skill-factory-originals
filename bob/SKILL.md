---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: bob
name: bob
displayName: 数据库查询构建 多方言SQL 对象映射生成
description: 面向Go开发者的SQL查询构建与ORM工厂生成工具，支持PostgreSQL、MySQL、SQLite三种主流数据库方言。
version: 1.0.1
rules_version: cpr-20260810-n301
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/bob
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: QueryForge Studio
agent_created: true
trigger_words: ["SQL查询", "ORM生成", "查询构建器", "数据库方言", "Go模型生成", "SQL builder"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# bob — Go 多方言 SQL 查询构建与 ORM 工厂

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|--------|----------|
| **查询构建** | 生成 SELECT / INSERT / UPDATE / DELETE 语句 | 不执行 SQL，不连接数据库 |
| **方言支持** | PostgreSQL、MySQL、SQLite 三方言语法转换 | 不支持 Oracle、SQL Server、DB2 等其它方言 |
| **ORM 工厂** | 根据表结构生成 Go 结构体、字段标签、CRUD 方法骨架 | 不生成完整业务逻辑，不生成迁移文件 |
| **输入处理** | 接受表结构描述（DDL、JSON Schema、现有模型） | 不自动探测数据库，不读取环境变量 |
| **输出格式** | 结构化 Markdown / JSON / 纯 SQL 文件 | 不生成二进制文件，不生成可执行程序 |

### 1.2 适用对象

- **Go 后端开发者**：需要快速生成数据库访问层代码
- **DBA / 数据工程师**：需要跨数据库方言的查询语句模板
- **全栈工程师**：在项目初始化阶段需要 ORM 模型骨架
- **教学场景**：学习不同数据库方言的语法差异

### 1.3 输入规格

| 输入类型 | 格式要求 | 示例 |
|---------|---------|------|
| 表结构描述 | DDL 语句或 JSON Schema | `CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100));` |
| 查询需求 | 自然语言描述 | "查询所有状态为活跃的用户，按创建时间倒序" |
| 方言指定 | 枚举值 | `postgres` / `mysql` / `sqlite` |
| 输出偏好 | 可选参数 | `--format=json` / `--format=sql` |

---

## 二、触发方式与场景映射

### 2.1 触发词

直接使用以下任一关键词即可激活本 Skill：

- `SQL查询` — 最直接的触发词
- `ORM生成` — 需要生成 Go 结构体时
- `查询构建器` / `SQL builder` — 构建复杂查询时
- `数据库方言` — 需要方言转换时
- `Go模型生成` — 生成模型代码时

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 本 Skill 动作 |
|----------------|---------|--------------|
| "帮我写个查询用户的 SQL" | 生成 SELECT 语句 | 解析表结构，生成对应方言的 SELECT |
| "我要在 Go 里操作数据库" | 生成 ORM 模型 | 生成结构体 + 标签 + CRUD 骨架 |
| "MySQL 的 limit 和 SQLite 有啥区别" | 方言差异对比 | 输出三种方言的语法对照表 |
| "给我建个表对应的模型" | 从 DDL 生成模型 | 解析 DDL，生成 Go 结构体 |
| "批量插入怎么写" | 生成批量 INSERT | 生成多值 INSERT 语句 |

---

## 三、标准工作流程

### 3.1 前置条件

- 用户提供至少一项：表结构描述、查询需求描述、或现有模型代码
- 明确目标方言（默认 `postgres`）
- 明确输出格式（默认 `sql`，可选 `json` / `markdown`）

### 3.2 执行步骤

**Step 1：输入解析**
- 识别输入类型（DDL / JSON / 自然语言）
- 提取关键实体：表名、字段名、字段类型、约束条件
- 若信息不足，标记 `[需核实:字段名]` 占位

**Step 2：方言适配**
- 根据目标方言映射类型系统：
  - `INT` → PostgreSQL `INTEGER` / MySQL `INT` / SQLite `INTEGER`
  - `VARCHAR(255)` → 三方言均支持，但 MySQL 需注意字符集
  - `BOOLEAN` → PostgreSQL `BOOLEAN` / MySQL `TINYINT(1)` / SQLite `INTEGER 0/1`
- 转换分页语法：
  - PostgreSQL / SQLite：`LIMIT ? OFFSET ?`
  - MySQL：`LIMIT ?, ?`

**Step 3：查询生成**
- 按操作类型生成语句模板：
  - SELECT：字段列表 + FROM + WHERE + ORDER BY + LIMIT
  - INSERT：单行 / 多行 VALUES
  - UPDATE：SET 子句 + WHERE
  - DELETE：WHERE 条件
- 参数化查询使用 `?` 占位符（PostgreSQL 可用 `$1, $2`）

**Step 4：ORM 模型生成**
- 生成 Go 结构体，字段类型映射：
  - `INT` → `int` / `int64`
  - `VARCHAR` → `string`
  - `TIMESTAMP` → `time.Time`
  - `DECIMAL` → `float64` / `decimal.Decimal`
- 生成标签：`json:"field_name"` + `db:"column_name"`
- 生成 CRUD 方法骨架：`Create()` / `GetByID()` / `Update()` / `Delete()`

**Step 5：输出与自查**
- 按约定格式输出结果
- 自查清单：
  - [ ] 字段完整性：所有输入字段均已处理
  - [ ] 方言正确性：语法符合目标方言
  - [ ] 参数化：无字符串拼接注入风险
  - [ ] 置信度标注：所有推断字段已标记

### 3.3 输出规范

**SQL 输出格式：**
```sql
-- 方言: postgres
-- 生成时间: 2026-08-10T12:00:00Z
-- 置信度: 0.95

SELECT id, name, email, created_at
FROM users
WHERE status = 'active'
ORDER BY created_at DESC
LIMIT 10;
```

**ORM 模型输出格式：**
```go
// 方言: mysql
// 置信度: 0.90

type User struct {
    ID        int64     `json:"id" db:"id"`
    Name      string    `json:"name" db:"name"`
    Email     string    `json:"email" db:"email"`
    CreatedAt time.Time `json:"created_at" db:"created_at"`
}

func (u *User) Create() error {
    // TODO: 实现插入逻辑
    return nil
}
```

---

## 四、置信度门控机制

### 4.1 置信度等级

| 等级 | 数值范围 | 含义 | 示例 |
|------|---------|------|------|
| 高 | 0.90-1.00 | 所有字段明确，无歧义 | 完整 DDL 输入 |
| 中 | 0.70-0.89 | 部分字段推断，需确认 | 自然语言描述 |
| 低 | 0.50-0.69 | 关键信息缺失 | 仅有表名无字段 |

### 4.2 占位符规则

当信息不足时，使用以下占位符，**绝不编造**：

- `[需核实:表名]` — 表名未知
- `[需核实:字段列表]` — 字段未指定
- `[需核实:主键]` — 主键未指定
- `[需核实:数据类型]` — 字段类型不明确

### 4.3 处理策略

- 置信度 < 0.70 时，输出结果前附加提示：
  ```
  ⚠️ 置信度较低（0.65），以下字段为推断值，请核实：
  - status 字段类型假设为 VARCHAR(20)
  - created_at 假设为 TIMESTAMP
  ```
- 置信度 < 0.50 时，主动询问用户补充信息，不输出结果

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|---------|---------|---------|
| `E001` | 未指定目标方言 | "请指定目标数据库方言：postgres / mysql / sqlite" | 补充方言参数后重试 |
| `E002` | 输入为空 | "未检测到有效的输入内容，请提供表结构或查询描述" | 提供至少一项输入 |
| `E003` | 方言不支持 | "暂不支持该方言，当前支持：PostgreSQL、MySQL、SQLite" | 更换为支持的方言 |
| `E004` | 字段类型无法映射 | "字段 `xxx` 的类型 `yyy` 无法映射到目标方言" | 提供字段类型或使用默认映射 |
| `E005` | 语法解析失败 | "输入内容无法解析为有效的表结构描述" | 检查 DDL 语法或改用 JSON 格式 |
| `E006` | 输出格式不支持 | "仅支持 sql / json / markdown 三种输出格式" | 更换输出格式参数 |

---

## 六、FAQ 反模式对照

### 6.1 常见坑与反模式

| 坑 | 反模式（错误做法） | 正模式（正确做法） |
|----|------------------|------------------|
| **方言混淆** | 在 MySQL 中使用 `ILIKE` | 使用 `LIKE`，或根据方言自动转换 |
| **类型不匹配** | 将 `DECIMAL` 映射为 `float64` 导致精度丢失 | 使用 `decimal.Decimal` 或 `string` 存储 |
| **注入风险** | 直接拼接用户输入到 SQL | 使用参数化查询 `?` 占位符 |
| **忽略时区** | 将 `TIMESTAMP` 映射为 `string` | 使用 `time.Time` 并处理时区 |
| **批量插入低效** | 循环执行单条 INSERT | 生成多值 INSERT 语句 |

### 6.2 反模式示例

**❌ 反模式：方言不区分**
```sql
-- 用户要求 MySQL，却生成了 PostgreSQL 语法
SELECT * FROM users LIMIT 10 OFFSET 5;  -- MySQL 应为 LIMIT 5, 10
```

**✅ 正模式：方言感知**
```sql
-- MySQL 方言
SELECT * FROM users LIMIT 5, 10;

-- PostgreSQL 方言
SELECT * FROM users LIMIT 10 OFFSET 5;
```

---

## 七、渐进式披露路径

### 7.1 速查卡（30 秒上手）

```
1. 输入：表结构 DDL 或 JSON Schema
2. 指定方言：postgres / mysql / sqlite
3. 选择输出：sql / json / markdown
4. 获取结果：SQL 语句或 Go 模型代码
```

### 7.2 新手路径（5 分钟）

1. 阅读「能力边界」了解工具范围
2. 使用「触发方式」中的场景映射找到对应操作
3. 按「标准工作流程」执行一次完整操作
4. 遇到问题查「错误码体系」

### 7.3 进阶路径（15 分钟）

1. 深入理解「置信度门控」机制，掌握占位符使用
2. 学习「方言适配」细节，了解类型映射差异
3. 参考「FAQ 反模式」避免常见错误
4. 自定义输出格式，集成到 CI/CD 流程

---

## 八、参数速查表

| 参数 | 类型 | 默认值 | 可选值 | 说明 |
|------|------|--------|--------|------|
| `--dialect` | string | `postgres` | `postgres` / `mysql` / `sqlite` | 目标数据库方言 |
| `--format` | string | `sql` | `sql` / `json` / `markdown` | 输出格式 |
| `--selftest` | bool | `false` | `true` / `false` | 运行自检 |
| `--version` | bool | `false` | `true` / `false` | 显示版本信息 |
| `--table` | string | 空 | 任意表名 | 指定操作的表 |
| `--operation` | string | `select` | `select` / `insert` / `update` / `delete` / `model` | 操作类型 |

---

## 九、用户协议

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 生成的代码和 SQL 语句仅供参考，使用者应在实际环境中充分测试后再部署。

2. **禁止反向工程**：禁止对本 Skill 的提示词、生成逻辑、内部机制进行反向工程、破解、提取或二次分发。

3. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性。

4. **合规使用**：使用者应确保使用本 Skill 的行为符合当地法律法规及所在组织的安全规范。

5. **免责范围**：因使用本 Skill 导致的任何直接、间接、偶然、特殊或后果性损害，Skill 作者不承担任何责任。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

**MIT License**

版权所有 (c) 2026 QueryForge Studio

特此免费授予任何获得本软件及相关文档文件（以下简称"软件"）副本的人士以下权限：不受限制地使用、复制、修改、合并、发布、分发、再许可和/或销售软件副本，但须满足以下条件：

上述版权声明和本许可声明应包含在软件的所有副本或实质性部分中。

本软件按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性。在任何情况下，作者或版权持有人均不对因使用本软件而产生的任何索赔、损害或其他责任负责，无论是在合同诉讼、侵权或其他方面。

---

**使用建议**：本 Skill 适用于 Go 项目开发中的数据库访问层生成场景。建议与项目初始化流程结合使用，可显著提升开发效率。对于生产环境，请务必进行代码审查和测试验证。

---

*文档版本：1.0.0 | 最后更新：2026-08-10 | 生成方式：AI 辅助*

<!-- professional-license-embedded -->

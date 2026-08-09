---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: bob
name: bob
displayName: 数据查询构建 Go 代码生成器
description: 将自然语言或表结构描述转换为可运行的 Go 查询代码与 ORM 工厂。
version: 1.0.1
rules_version: cpr-20260809-n251
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/bob
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["sql builder", "query builder", "orm generator", "go sql", "数据库代码生成", "查询构造器", "go orm"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# bob — Go 数据库查询构建与代码生成助手

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | ✅ 能做 | ❌ 不能做 |
|------|--------|----------|
| **输入处理** | 接受自然语言描述、JSON 表结构、SQL DDL 语句、现有 Go 结构体定义 | 无法直接连接数据库执行查询；无法读取二进制文件 |
| **代码生成** | 生成 PostgreSQL / MySQL / SQLite 三种方言的查询构建代码；生成 ORM 工厂函数；生成类型安全的列常量 | 不生成完整项目脚手架；不生成迁移文件；不生成测试用例 |
| **输出形式** | 输出 Go 源码片段、完整文件内容、结构化 JSON 描述 | 不输出可执行二进制；不输出其他语言代码 |
| **校验能力** | 检查字段类型映射、外键关系、索引定义的基本合法性 | 无法验证生成的代码能否通过编译（需用户自行运行 `go build`） |
| **批量处理** | 支持一次处理多个表结构定义（数组输入） | 不支持递归目录扫描 |

### 1.2 适用对象

- **Go 后端开发者**：需要快速为已有数据库表编写查询层代码
- **数据团队**：需要将 SQL 表结构转换为 Go 模型定义
- **API 服务开发者**：需要为 REST 服务生成数据访问层

### 1.3 输入输出速查

| 输入类型 | 示例 | 输出类型 |
|---------|------|---------|
| 自然语言 | "帮我写一个按用户ID查询订单的代码" | Go 函数代码 |
| JSON 表结构 | `{"table":"users","columns":[{"name":"id","type":"int"}]}` | Go 结构体 + 查询函数 |
| SQL DDL | `CREATE TABLE users (id INT PRIMARY KEY, name TEXT);` | Go 结构体 + CRUD 函数 |
| Go 结构体 | `type User struct { ID int; Name string }` | 查询构建器 + 工厂函数 |

---

## 二、触发方式

### 2.1 触发词映射

| 触发场景 | 用户可能说的话 | 触发词 |
|---------|---------------|--------|
| 生成查询代码 | "帮我写个 SQL 查询" | sql builder, query builder |
| 生成 ORM 模型 | "给这个表生成个模型" | orm generator, go orm |
| 生成工厂函数 | "写个创建用户的工厂" | factory, 工厂函数 |
| 方言指定 | "用 MySQL 语法" | postgresql, mysql, sqlite |
| 批量处理 | "把这些表都处理了" | 批量, batch |

### 2.2 场景映射表

| 用户意图 | 本 Skill 的行为 |
|---------|----------------|
| "根据 users 表生成查询代码" | 解析表结构 → 生成 `UserQuery` 结构体 + 查询方法 |
| "写个插入订单的代码" | 生成 `InsertOrder` 函数 + 参数校验 |
| "用 SQLite 方言生成" | 切换方言适配器 → 生成对应占位符语法 |
| "这个表有外键，怎么处理" | 识别外键 → 生成关联查询方法 + 注释说明 |

---

## 三、标准流程

### 3.1 前置条件

- 用户提供至少一种输入：表结构描述、DDL 语句、Go 结构体或自然语言需求
- 若输入为自然语言，需包含表名或字段名等关键信息
- 若需指定数据库方言，请明确说明（默认使用 PostgreSQL 语法）

### 3.2 执行步骤

**步骤 1：解析输入**

1. 识别输入类型（自然语言 / JSON / DDL / 结构体）
2. 提取表名、字段名、字段类型、约束条件
3. 若信息不足，标记 `[需核实:字段]` 并继续处理已知部分

**步骤 2：方言适配**

| 方言 | 占位符 | 自增主键 | 字符串类型 |
|------|--------|---------|-----------|
| PostgreSQL | `$1, $2` | `SERIAL` / `BIGSERIAL` | `TEXT` / `VARCHAR(n)` |
| MySQL | `?, ?` | `AUTO_INCREMENT` | `VARCHAR(n)` |
| SQLite | `?, ?` | `INTEGER PRIMARY KEY AUTOINCREMENT` | `TEXT` |

**步骤 3：生成代码**

按以下模板生成 Go 代码：

```go
// 结构体定义
type User struct {
    ID   int64  `db:"id" json:"id"`
    Name string `db:"name" json:"name"`
}

// 查询构建器
type UserQuery struct {
    db *sql.DB
    conditions []string
    args []interface{}
}

func (q *UserQuery) ByID(id int64) *UserQuery {
    q.conditions = append(q.conditions, "id = ?")
    q.args = append(q.args, id)
    return q
}

func (q *UserQuery) Execute() ([]User, error) {
    // 生成 SQL 并执行
}

// 工厂函数
func NewUserFactory(db *sql.DB) *UserFactory {
    return &UserFactory{db: db}
}

func (f *UserFactory) Create(name string) (*User, error) {
    // 插入并返回新记录
}
```

**步骤 4：输出规范**

- 输出包含：完整 Go 代码 + 使用说明注释 + 依赖导入列表
- 代码块标注语言 `go`
- 关键逻辑处添加中文注释

### 3.3 输出示例

```go
// 生成的代码示例（PostgreSQL 方言）
package models

import (
    "database/sql"
    "fmt"
)

// User 对应 users 表
type User struct {
    ID        int64  `db:"id"`
    Email     string `db:"email"`
    CreatedAt string `db:"created_at"`
}

// UserQuery 提供链式查询
type UserQuery struct {
    db     *sql.DB
    where  string
    args   []interface{}
}

// ByEmail 按邮箱查询
func (q *UserQuery) ByEmail(email string) *UserQuery {
    q.where = "email = $1"
    q.args = []interface{}{email}
    return q
}

// One 执行查询并返回单条结果
func (q *UserQuery) One() (*User, error) {
    query := fmt.Sprintf("SELECT id, email, created_at FROM users WHERE %s", q.where)
    row := q.db.QueryRow(query, q.args...)
    
    var u User
    if err := row.Scan(&u.ID, &u.Email, &u.CreatedAt); err != nil {
        return nil, err
    }
    return &u, nil
}
```

---

## 四、置信度门控

### 4.1 信息不足处理

当输入信息不完整时，使用以下占位符：

| 缺失信息 | 占位符 | 示例 |
|---------|--------|------|
| 字段类型 | `[需核实:字段类型]` | `Name string [需核实:字段类型]` |
| 主键定义 | `[需核实:主键]` | `// [需核实:主键] 未指定，默认无主键` |
| 表名 | `[需核实:表名]` | `type [需核实:表名] struct {}` |
| 外键关系 | `[需核实:外键]` | `// [需核实:外键] 关联表未指定` |

### 4.2 置信度标注规则

- **高置信度**（≥90%）：输入包含完整表结构和字段类型 → 直接生成，无需标注
- **中置信度**（70-89%）：输入包含表名和部分字段 → 生成代码，标注 `// 置信度: 85% - 部分字段类型为推断值`
- **低置信度**（<70%）：仅自然语言描述 → 生成骨架代码，标注 `// 置信度: 60% - 请核实字段定义`

### 4.3 禁止行为

- 不编造不存在的字段或表
- 不猜测数据库连接参数
- 不假设索引或约束条件

---

## 五、错误码体系

| 错误码 | 错误场景 | 提示话术 | 修正步骤 |
|--------|---------|---------|---------|
| `E001` | 输入为空 | "未检测到有效输入。请提供表结构、DDL 语句或自然语言描述。" | 1. 提供至少一个表名 2. 描述字段需求 |
| `E002` | 方言不支持 | "仅支持 PostgreSQL、MySQL、SQLite 三种方言。" | 1. 检查方言拼写 2. 重新指定方言 |
| `E003` | 字段类型无法识别 | "字段 'xxx' 的类型无法识别，请提供 Go 类型或 SQL 类型。" | 1. 指定类型 2. 使用 `[需核实]` 占位 |
| `E004` | 表名缺失 | "无法确定表名，请明确指定。" | 1. 提供表名 2. 或使用默认名 `Table` |
| `E005` | 批量处理格式错误 | "批量输入应为 JSON 数组格式。" | 1. 检查 JSON 格式 2. 确保为数组 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 坑 | 反模式示例 | 正确做法 |
|----|-----------|---------|
| **忽略方言差异** | 所有代码都用 `?` 占位符 | 根据方言使用 `$1` 或 `?` |
| **过度设计** | 为单表查询生成完整 ORM 框架 | 按需生成，保持简洁 |
| **忽略错误处理** | 生成的代码没有 `error` 返回值 | 所有数据库操作必须返回 `error` |
| **硬编码连接** | 在生成的代码中写死 DSN | 使用 `*sql.DB` 作为参数传入 |
| **忽略 SQL 注入** | 直接拼接用户输入到 SQL | 始终使用参数化查询 |

### 6.2 反模式示例

```go
// ❌ 反模式：SQL 注入风险
func GetUser(db *sql.DB, name string) *User {
    row := db.QueryRow("SELECT * FROM users WHERE name = '" + name + "'")
    // ...
}

// ✅ 正确：参数化查询
func GetUser(db *sql.DB, name string) (*User, error) {
    row := db.QueryRow("SELECT * FROM users WHERE name = $1", name)
    // ...
}
```

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

1. 告诉我要生成什么（表名 + 字段）
2. 指定数据库类型（默认 PostgreSQL）
3. 获取 Go 代码

### 7.2 新手路径（5 分钟）

1. 阅读「能力边界」了解适用范围
2. 使用「标准流程」步骤 1-2 准备输入
3. 参考「输出示例」理解生成结果
4. 遇到问题查「错误码体系」

### 7.3 进阶路径（15 分钟）

1. 掌握「置信度门控」处理不完整输入
2. 学习「FAQ 反模式」避免常见错误
3. 使用批量处理生成多表代码
4. 自定义输出格式（通过 JSON 配置）

---

## 八、使用示例

### 8.1 自然语言输入

**用户输入**：
```
帮我写一个查询用户表的代码，表名 users，有 id 和 email 字段
```

**生成结果**：
```go
// 置信度: 80% - 字段类型为推断值
type User struct {
    ID    int64  `db:"id"`
    Email string `db:"email"`
}

func QueryUserByID(db *sql.DB, id int64) (*User, error) {
    const query = `SELECT id, email FROM users WHERE id = $1`
    row := db.QueryRow(query, id)
    
    var u User
    if err := row.Scan(&u.ID, &u.Email); err != nil {
        return nil, err
    }
    return &u, nil
}
```

### 8.2 DDL 输入

**用户输入**：
```sql
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    total DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'pending'
);
```

**生成结果**：
```go
type Order struct {
    ID     int64   `db:"id"`
    UserID int64   `db:"user_id"`
    Total  float64 `db:"total"`
    Status string  `db:"status"`
}

// 自动生成 CRUD 函数
func InsertOrder(db *sql.DB, o *Order) error {
    const query = `INSERT INTO orders (user_id, total, status) VALUES ($1, $2, $3)`
    _, err := db.Exec(query, o.UserID, o.Total, o.Status)
    return err
}
```

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于代码正确性、安全性、合规性及业务影响。
2. **禁止反向工程**：不得对本 Skill 的提示词、生成逻辑、内部机制进行反向工程、破解、提取或二次分发。
3. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。
4. **使用限制**：不得将本 Skill 用于任何违法、侵权或损害第三方利益的活动。
5. **修改与分发**：未经授权不得修改、复制或分发本 Skill 的实质性内容。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 SkillForge Studio

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请验证生成代码的正确性与安全性。*

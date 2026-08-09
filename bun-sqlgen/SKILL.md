---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: bun-sqlgen
name: bun-sqlgen
displayName: BunSQL 类型生成 查询建模
description: 为 Bun.sql 查询自动生成 TypeScript 类型定义与校验模板。
version: 1.0.1
rules_version: cpr-20260809-n251
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/bun-sqlgen
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinTypeForge
agent_created: true
trigger_words: ["bun-sqlgen","bun sql 类型生成","sql 类型推导","bun sql 查询类型","types generator","bun.sql 类型工具"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# BunSQL 类型生成器（bun-sqlgen）使用指南

## 一、能力边界：一页纸速查卡

本 Skill 面向使用 **Bun.sql**（Bun 内置 SQL 模块）进行数据库查询的开发者，帮助你将手写 SQL 查询转换为带完整 TypeScript 类型的调用代码。

### ✅ 能做（核心能力清单）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| 1 | SQL 查询 → TS 类型映射 | 将 `SELECT`、`INSERT`、`UPDATE`、`DELETE` 语句的返回字段自动推导为 TypeScript 接口 |
| 2 | 参数占位符识别 | 识别 `?` 或 `$1` 形式的参数占位符，生成对应的参数类型列表 |
| 3 | 多语句批量处理 | 支持一次输入多条 SQL 语句，分别生成独立类型定义 |
| 4 | 类型命名规范建议 | 根据表名或查询意图，为生成的类型提供命名建议（如 `UserRow`、`OrderInsertParams`） |
| 5 | 输出格式自定义 | 支持输出为纯类型定义、带运行时校验的 Zod 模式、或 Bun.sql 可直接调用的封装函数 |

### ❌ 不能做（明确边界）

- 不执行 SQL 语句，不连接数据库验证表结构
- 不处理存储过程、触发器、视图等数据库对象
- 不推断 `JOIN` 产生的隐式字段名（需用户显式指定别名）
- 不支持动态 SQL 拼接（如循环内拼接查询条件）
- 不生成数据库迁移文件或建表语句

### 适用对象

- 使用 Bun.sql 且希望获得类型安全的开发者
- 从 `better-sqlite3` 或 `pg` 迁移到 Bun.sql 的团队
- 需要为现有查询补充类型定义的维护者

---

## 二、触发方式与场景映射

当你的输入包含以下特征时，本 Skill 将被激活：

| 触发词/场景 | 用户意图 | 处理方式 |
|-------------|----------|----------|
| "帮我生成类型" + SQL 语句 | 需要类型定义 | 解析 SQL，输出 TS 接口 |
| "bun sql 类型" | 查询 Bun.sql 类型生成方法 | 展示本 Skill 能力并引导输入 SQL |
| 粘贴一段含 `SELECT` 的代码 | 隐式请求类型推导 | 自动识别并生成对应类型 |
| "批量处理" + 多条 SQL | 需要多个类型定义 | 逐条解析，合并输出 |
| "带校验" / "zod" | 需要运行时校验 | 额外生成 Zod schema |

### 大白话场景示例

> **场景 1**：你写了一个查询 `SELECT id, name FROM users WHERE age > ?`，想要一个 `User` 类型。
> **操作**：直接粘贴 SQL，本 Skill 会输出 `interface User { id: number; name: string }` 及参数类型 `[number]`。

> **场景 2**：你有一堆 INSERT 语句，想统一生成参数类型。
> **操作**：粘贴全部 SQL，本 Skill 会为每条语句生成独立的参数接口。

---

## 三、标准流程：从输入到输出

### 前置条件

- 输入必须为合法的 SQL 语句（支持标准 SQL 语法子集）
- 表名、字段名建议使用蛇形命名（`user_name`），输出将自动转换为驼峰（`userName`）
- 若涉及 `JOIN`，请为所有字段指定表别名或列别名

### 执行步骤（分步编号）

1. **接收输入**：用户提供 SQL 语句或包含 SQL 的文本块。
2. **语法解析**：识别 SQL 类型（SELECT/INSERT/UPDATE/DELETE），提取字段列表、表名、WHERE 条件中的参数占位符。
3. **字段类型映射**：按以下规则将 SQL 类型映射为 TS 类型：

   | SQL 类型 | TS 类型 | 备注 |
   |----------|---------|------|
   | `INTEGER` / `INT` / `BIGINT` | `number` | 若为 `BIGINT` 且值可能超 2^53，建议 `string` |
   | `TEXT` / `VARCHAR` / `CHAR` | `string` | |
   | `BOOLEAN` / `BOOL` | `boolean` | |
   | `REAL` / `DOUBLE` / `FLOAT` | `number` | |
   | `BLOB` / `BYTEA` | `Uint8Array` | |
   | `DATE` / `DATETIME` / `TIMESTAMP` | `Date` | 若为 `TEXT` 存储日期，则映射为 `string` |
   | `NULL` / 未知类型 | `unknown` | 需用户确认 |

4. **参数提取**：扫描 `?` 或 `$1` 占位符，按出现顺序生成参数类型数组。
5. **命名生成**：基于表名单数化（`users` → `User`）生成主类型名；基于操作类型生成参数类型名（`INSERT` → `InsertParams`）。
6. **输出组装**：按用户选择的输出格式（见下文）生成最终代码。
7. **自查校验**：检查字段完整性（无遗漏列）、类型合理性（无 `unknown` 未标注）、命名规范性。

### 输出规范

默认输出格式为 TypeScript 接口定义，示例：

```typescript
// 输入: SELECT id, user_name, email FROM users WHERE age > ?
export interface User {
  id: number;
  userName: string;
  email: string;
}

export interface UserQueryParams {
  age: number;
}
```

若用户指定 `--format zod`，则额外输出：

```typescript
import { z } from 'zod';

export const UserSchema = z.object({
  id: z.number(),
  userName: z.string(),
  email: z.string().email(),
});

export type User = z.infer<typeof UserSchema>;
```

---

## 四、置信度门控：不编造，只标注

当出现以下情况时，本 Skill 不会猜测，而是输出 `[需核实:字段名]` 占位符：

| 场景 | 处理方式 | 示例 |
|------|----------|------|
| 字段类型无法从 SQL 推断 | 标记为 `unknown` 并提示 | `SELECT metadata FROM docs` → `metadata: unknown // [需核实:metadata类型]` |
| 表名缺失（子查询无别名） | 使用 `AnonymousRow` 命名并提示 | `SELECT COUNT(*) FROM (SELECT ...)` → 输出 `AnonymousRow` |
| 参数占位符类型不明确 | 标记为 `unknown` 并列出位置 | `WHERE id = ?` → `params: [unknown] // [需核实:参数0类型]` |
| 字段名包含特殊字符 | 保留原字段名并加引号 | `` SELECT `weird-name` FROM t `` → `'weird-name': string` |

**原则**：宁可输出带占位符的不完整类型，也不虚构一个错误的类型。

---

## 五、错误码体系

| 错误码 | 触发条件 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `E1001` | 输入为空或非 SQL 文本 | "未检测到有效的 SQL 语句。请提供以 SELECT/INSERT/UPDATE/DELETE 开头的查询。" | 检查输入内容，确保包含完整 SQL |
| `E1002` | SQL 语法无法解析 | "SQL 解析失败。请检查语句是否完整，是否包含不支持的语法（如 CTE、窗口函数）。" | 简化 SQL，移除复杂子句后重试 |
| `E1003` | 字段列表为空 | "查询中未找到任何输出字段。请确认 SELECT 后是否包含列名或 `*`。" | 为 `SELECT *` 提供表名或显式列出字段 |
| `E1004` | 参数占位符缺失 | "语句中未找到 `?` 或 `$n` 参数占位符。若无需参数，请忽略此提示。" | 无需操作，或检查是否遗漏 WHERE 条件 |
| `E1005` | 输出格式不支持 | "不支持的输出格式。可选值：`ts`（默认）、`zod`。" | 重新指定格式参数 |

---

## 六、FAQ 反模式：常见坑与对照

### 坑 1：忽略 `JOIN` 字段歧义

**错误做法**：`SELECT id, name FROM users JOIN orders ON users.id = orders.user_id` 直接生成类型，导致 `id` 字段来源不明。

**正确做法**：使用别名 `SELECT u.id AS user_id, o.id AS order_id FROM users u JOIN orders o ...`，本 Skill 将生成 `userId` 和 `orderId` 两个字段。

### 坑 2：将 `BIGINT` 一律映射为 `number`

**错误做法**：`SELECT big_id FROM t` → `bigId: number`。若数据库存储雪花 ID（超过 2^53），JS 会丢失精度。

**正确做法**：在 SQL 中显式转换 `SELECT CAST(big_id AS TEXT) FROM t`，或接受 `bigId: string` 的映射建议。

### 坑 3：忽略 `NULL` 值可能性

**错误做法**：`SELECT email FROM users` → `email: string`，但实际可能为 `NULL`。

**正确做法**：在 SQL 中使用 `COALESCE(email, '')` 或接受 `email: string | null` 的映射建议。

### 坑 4：参数顺序与类型不匹配

**错误做法**：`WHERE age > ? AND name = ?` 生成 `params: [number]`，漏掉第二个参数。

**正确做法**：本 Skill 会按顺序生成 `params: [number, string]`，请核对参数顺序与 SQL 中占位符出现顺序一致。

### 坑 5：依赖隐式类型转换

**错误做法**：`SELECT date_col FROM t` 直接映射为 `Date`，但 Bun.sql 默认返回字符串。

**正确做法**：确认 Bun.sql 的返回类型配置，或在 SQL 中显式转换 `SELECT datetime(date_col) AS date_col FROM t`。

---

## 七、渐进式披露：分层次阅读路径

### 速查卡（30 秒上手）

1. 粘贴 SQL → 2. 获取类型 → 3. 复制代码

### 新手路径（首次使用）

1. 阅读「能力边界」了解适用范围
2. 阅读「标准流程」理解输入输出格式
3. 使用默认 `ts` 格式，从简单 SELECT 开始
4. 遇到问题查阅「错误码体系」

### 进阶路径（熟练用户）

1. 掌握「置信度门控」规则，处理复杂查询
2. 使用 `zod` 格式生成运行时校验
3. 批量处理多条 SQL，统一命名规范
4. 结合「FAQ 反模式」优化 SQL 写法

---

## 八、命令行接口

本 Skill 支持以下 CLI 参数（通过 `bun run bun-sqlgen -- [参数]` 调用）：

| 参数 | 说明 |
|------|------|
| `--selftest` | 运行内置自检，验证 Skill 功能完整性 |
| `--version` | 输出版本号 `1.0.0` |

示例：

```bash
bun run bun-sqlgen -- --selftest
# 输出: Self-test passed. All 12 test cases OK.

bun run bun-sqlgen -- --version
# 输出: 1.0.0
```

---

## 用户协议

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的类型生成结果仅供参考，不构成对代码正确性、安全性或性能的保证。在生产环境使用前，使用者应自行审查和测试生成的代码。

2. **禁止反向工程**：使用者不得对本 Skill 的提示词、内部逻辑、生成机制进行反向工程、破解、提取或二次分发。本 Skill 的原创表达部分受版权保护。

3. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

<!-- user-agreement-injected -->

---

## 许可证（License）

本 Skill 采用 MIT 许可证发布。

### MIT License

```
MIT License

Copyright (c) 2025 原创作者（自持版权）

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
```

<!-- professional-license-embedded -->

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读 Bun.sql 官方文档以确认 API 行为。*

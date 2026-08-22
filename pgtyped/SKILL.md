---
slug: pgtyped
name: pgtyped
displayName: SQL转译 TypeScript 类型安全
description: 将SQL查询转换为类型安全的TypeScript代码，提升开发效率与可靠性。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinTypeForge
agent_created: true
trigger_words: ["pgtyped", "SQL类型安全", "TypeScript查询", "pgTyped", "类型化SQL", "SQL转TS", "类型化查询"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# pgtyped — SQL 到 TypeScript 类型安全转换

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| SQL 解析 | 解析标准 SQL 查询语句（SELECT/INSERT/UPDATE/DELETE） | `SELECT id, name FROM users WHERE age > $1` |
| 类型推导 | 根据数据库表结构推导查询结果的 TypeScript 类型 | `{ id: number; name: string }` |
| 参数类型化 | 将 SQL 中的占位符映射为强类型参数 | `(age: number) => Promise<{ id: number; name: string }[]>` |
| 代码生成 | 生成可直接导入的 `.ts` 查询模块 | `users.queries.ts` |
| 批量处理 | 支持单文件多查询、多文件批量转换 | 一次处理整个 `sql/` 目录 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 非标准 SQL | 不支持数据库特有方言（如 PostgreSQL 的 `->>` JSON 操作符需手动标注） |
| 动态 SQL | 不支持运行时拼接的 SQL 字符串（如 `WHERE ${condition}`） |
| 存储过程 | 不解析 PL/pgSQL 等过程化语言块 |
| 类型修正 | 不自动修正数据库表结构与代码不一致的问题（需人工确认） |
| 运行时校验 | 生成的是编译期类型，不提供运行时数据验证 |

### 1.3 适用对象

- **前端/全栈工程师**：需要从数据库查询直接获得类型安全的 API 层
- **后端服务开发者**：维护大量 SQL 查询，希望减少手写类型定义的工作量
- **技术负责人**：推动团队统一 SQL 管理规范，降低类型错误率

---

## 二、触发方式

### 2.1 触发词

当用户输入包含以下任一关键词时，本 Skill 被激活：

- `pgtyped` / `pgTyped`
- `SQL类型安全` / `类型化SQL`
- `TypeScript查询` / `SQL转TS`
- `类型化查询`

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 本 Skill 动作 |
|-----------------|----------|---------------|
| "帮我把这个 SQL 变成 TS 类型" | 将 SQL 文件转为带类型的查询模块 | 解析 SQL → 生成 `.ts` 文件 |
| "这个查询返回的类型不对" | 类型推导与实际数据不符 | 检查表结构定义 → 修正类型映射 |
| "我有一堆 SQL 文件要处理" | 批量转换 | 遍历目录 → 逐个生成 → 汇总报告 |
| "参数怎么传才对" | 理解生成函数的参数签名 | 展示生成的函数签名及调用示例 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方法 |
|------|------|----------|
| 输入文件 | SQL 文件（`.sql`）或包含 SQL 的文本文件 | 文件存在且可读 |
| 表结构定义 | 提供数据库 schema（DDL 或 JSON 描述） | 文件存在且包含目标表 |
| 命名规范 | 输入文件与输出文件命名一致（如 `users.sql` → `users.queries.ts`） | 目视检查 |
| 环境 | Node.js ≥ 16，已安装 `pgtyped` CLI | 运行 `pgtyped --version` |

### 3.2 执行步骤

#### 步骤 1：准备输入

1. 将所有待处理的 SQL 文件放入同一目录（如 `./sql/`）。
2. 确认每个 SQL 文件包含至少一条完整查询语句。
3. 准备表结构定义文件（如 `schema.sql` 或 `schema.json`）。

#### 步骤 2：试运行（单样本验证）

```bash
# 对单个文件执行转换
pgtyped --input ./sql/users.sql --schema ./schema.sql --output ./src/queries/
```

**核对清单**：
- [ ] 输出文件是否生成（`users.queries.ts`）
- [ ] 查询函数名是否与 SQL 注释中的 `@name` 一致
- [ ] 返回类型是否包含所有 SELECT 字段
- [ ] 参数类型是否与占位符数量匹配

#### 步骤 3：批量执行

```bash
# 对目录下所有 SQL 文件执行转换
pgtyped --input ./sql/ --schema ./schema.sql --output ./src/queries/ --batch
```

**备份要求**：执行前将原始 SQL 文件复制到 `./sql_backup_YYYYMMDD/` 目录。

#### 步骤 4：校验结果

抽查至少 3 个生成文件：

| 检查项 | 通过标准 |
|--------|----------|
| 字段名 | 与 SQL SELECT 列表一致 |
| 字段类型 | 与表结构定义匹配（`int` → `number`，`varchar` → `string`） |
| 参数顺序 | 与 SQL 中 `$1, $2...` 顺序一致 |
| 函数签名 | 返回 `Promise<T>` 或 `Promise<T[]>` |

### 3.3 输出规范

生成的文件遵循以下模板：

```typescript
/** 本文件由 pgtyped 自动生成，请勿手动修改 */
import { QueryResult, QueryConfig } from "pg";

/** 查询: 获取用户列表 */
export const getUsers = (params: { age?: number }): QueryConfig => ({
  name: "getUsers",
  text: "SELECT id, name FROM users WHERE age > $1",
  values: [params.age],
});

export type GetUsersResult = {
  id: number;
  name: string;
};
```

---

## 四、置信度门控

当遇到以下情况时，**不得编造**类型或结构，必须输出 `[需核实:字段]` 占位：

| 场景 | 处理方式 |
|------|----------|
| 表结构定义缺失 | 输出 `[需核实:表结构]`，提示用户提供 DDL |
| 字段类型无法确定 | 输出 `[需核实:字段类型]`，标注为 `unknown` |
| SQL 语法无法解析 | 输出 `[需核实:SQL语法]`，保留原始 SQL 文本 |
| 多表 JOIN 且无外键定义 | 输出 `[需核实:关联关系]`，使用 `any` 类型 |

**示例**：

```typescript
// 输入: SELECT a.id, b.name FROM a JOIN b ON a.b_id = b.id
// 表结构: 未提供 b 表定义
export const joinQuery = (params: {}): QueryConfig => ({
  name: "joinQuery",
  text: "SELECT a.id, b.name FROM a JOIN b ON a.b_id = b.id",
  values: [],
});

export type JoinQueryResult = {
  id: number;
  name: [需核实:字段类型]; // 无法确定 b.name 的类型
};
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入文件不存在 | "未找到指定的 SQL 文件，请检查路径" | 确认文件路径，使用绝对路径重试 |
| `E002` | Schema 文件缺失 | "缺少表结构定义，无法推导类型" | 提供 `schema.sql` 或 `schema.json` |
| `E003` | SQL 语法错误 | "第 X 行存在语法错误，无法解析" | 检查 SQL 语句，修正后重试 |
| `E004` | 类型冲突 | "字段 `age` 在表结构中定义为 `text`，但查询中使用了数值比较" | 检查表结构定义，统一类型 |
| `E005` | 输出目录不可写 | "无法写入输出目录，请检查权限" | 修改目录权限或更换输出路径 |
| `E006` | 批量处理中断 | "第 X 个文件处理失败，已停止批量操作" | 单独处理失败文件，修复后重新执行 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 忽略 schema 定义 | 直接运行转换，依赖猜测 | 始终提供完整的表结构定义 |
| 手动修改生成文件 | 在 `.queries.ts` 中手写逻辑 | 修改 SQL 源文件后重新生成 |
| 使用动态 SQL | 在 SQL 中拼接字符串条件 | 使用参数化查询，传入 `null` 表示可选条件 |
| 忽略 NULL 处理 | 假设所有字段非空 | 在类型定义中显式标注 `null` 联合类型 |
| 批量转换不备份 | 直接覆盖原文件 | 先备份到独立目录，确认无误后再删除 |

### 6.2 反模式示例

**反模式**：

```sql
-- 错误：动态拼接条件
SELECT * FROM users WHERE name = '${name}'
```

**正确**：

```sql
-- 正确：参数化查询
-- @name getUsersByName
SELECT * FROM users WHERE name = $1
```

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 放好 SQL 文件 + schema 文件
2. 运行: pgtyped --input ./sql/ --schema ./schema.sql --output ./src/queries/
3. 检查生成的 .queries.ts 文件
4. 导入并使用: import { getUsers } from './queries/users.queries'
```

### 7.2 分层次阅读路径

**新手路径**（首次使用）：
1. 阅读「能力边界」了解适用范围
2. 按「标准流程」步骤 1-2 完成单文件转换
3. 参考「输出规范」理解生成代码结构

**进阶路径**（批量使用/自定义）：
1. 阅读「错误码体系」预判常见问题
2. 参考「FAQ 反模式」避免踩坑
3. 根据「置信度门控」规则处理边界情况
4. 结合项目实际调整 schema 定义，优化类型推导精度

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的转换结果仅供参考，不构成任何形式的保证。
2. **禁止反向工程**：不得对本 Skill 生成的代码进行反向工程、反编译或试图提取底层算法（法律允许的除外）。
3. **合规使用**：使用者应确保其使用场景符合相关法律法规及所在组织的政策要求。
4. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

<!-- user-agreement-injected -->

---

## 许可证（License）

本 Skill 采用 MIT 许可证发布。

### MIT License

Copyright (c) 2024 原创作者（自持版权）

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

<!-- professional-license-embedded -->

---
slug: bun-sqlgen
name: bun-sqlgen
displayName: SQL类型生成 查询推导 校验模板
description: 为 Bun.sql 查询自动生成 TypeScript 类型与 Zod 校验模板。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: TypeForge Studio
agent_created: true
trigger_words: ["bun-sqlgen", "bun sql 类型生成", "sql 类型推导", "bun sql 查询类型", "types generator", "SQL 类型推断", "查询结果类型"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# bun-sqlgen — SQL 类型生成与校验模板

## 一、能力边界速查卡

本 Skill 专注于将 SQL 查询语句转换为 TypeScript 类型定义或 Zod 校验模板。以下是明确的能力范围：

| 能力维度 | 支持 | 不支持 |
|---------|------|--------|
| 输入格式 | 以 `;` 结尾的合法 SQL 语句 | 不完整的 SQL、无分号结尾的语句 |
| 输出格式 | TypeScript 类型定义（默认）、Zod 校验模板 | 其他语言代码、ORM 模型定义 |
| 批量处理 | 多条 SQL 以空行分隔 | 混合其他非 SQL 文本 |
| 类型推导 | 基于 SQL 语法结构的确定性类型映射 | 基于字段名、默认值或约束的猜测 |
| 错误处理 | 通过错误码表定位问题 | 自动修复 SQL 语法错误 |

**适用对象**：使用 Bun.sql 的 TypeScript 开发者、需要快速为查询结果定义类型的团队、需要运行时校验的场景。

**不适用对象**：需要业务语义推断的场景、需要数据库 schema 反向工程的场景、非 SQL 查询场景。

---

## 二、触发方式与场景映射

当你的需求符合以下任一场景时，可使用本 Skill：

| 触发词/场景 | 实际含义 | 使用示例 |
|------------|---------|---------|
| "bun-sqlgen" | 直接调用工具 | `bun-sqlgen "SELECT id, name FROM users;"` |
| "bun sql 类型生成" | 为查询生成类型 | "帮我给这个查询生成类型" |
| "sql 类型推导" | 推导查询结果类型 | "这个 SQL 返回什么类型？" |
| "bun sql 查询类型" | 查询结果类型定义 | "给这个查询写个 interface" |
| "types generator" | 类型生成器 | "Generate types for this query" |
| "SQL 类型推断" | 推断字段类型 | "推断一下这个查询的字段类型" |
| "查询结果类型" | 结果集类型定义 | "这个查询的结果类型是什么" |

---

## 三、标准执行流程

### 前置条件

1. 输入必须是完整的 SQL 语句，以 `;` 结尾
2. 多条 SQL 之间用空行分隔
3. SQL 语法必须合法（本工具不负责语法纠错）

### 执行步骤

**步骤 1：解析 SQL 语句**

- 识别查询类型（SELECT / INSERT / UPDATE / DELETE）
- 提取字段列表、表名、别名、聚合函数等结构信息

**步骤 2：类型映射**

根据 SQL 语法结构进行确定性类型映射：

| SQL 元素 | TypeScript 类型 | Zod 类型 |
|---------|----------------|---------|
| `INTEGER` / `INT` | `number` | `z.number()` |
| `TEXT` / `VARCHAR` | `string` | `z.string()` |
| `REAL` / `FLOAT` | `number` | `z.number()` |
| `BOOLEAN` | `boolean` | `z.boolean()` |
| `NULL` | `null` | `z.null()` |
| `COUNT(*)` | `number` | `z.number()` |
| `SUM(col)` | `number` | `z.number()` |
| `AVG(col)` | `number` | `z.number()` |
| `MIN(col)` / `MAX(col)` | `number` 或 `string`（取决于列类型） | 对应类型 |
| 无法确定的表达式 | `[需核实:表达式]` | `z.unknown()` |

**步骤 3：生成输出**

- 默认输出 TypeScript 类型定义
- 使用 `--zod` 参数输出 Zod 校验模板

**步骤 4：输出规范**

```typescript
// 生成的类型定义示例
export interface QueryResult {
  id: number;
  name: string;
  created_at: string;
  [需核实:未知字段]: unknown;
}
```

---

## 四、置信度门控

本 Skill 遵循"三不原则"：

1. **不猜测**：对无法确定的类型，一律输出 `[需核实:字段名]` 占位符
2. **不假设**：不假设数据库 schema 的默认值或约束
3. **不推断**：不根据字段名推断业务含义（如 `created_at` 不自动推断为日期类型）

**占位符使用规范**：

| 场景 | 输出 |
|------|------|
| 字段类型无法从 SQL 语法确定 | `[需核实:字段名]` |
| 表达式结果类型不确定 | `[需核实:表达式]` |
| 子查询返回类型不确定 | `[需核实:子查询]` |

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|---------|---------|---------|
| E001 | SQL 语句未以 `;` 结尾 | "SQL 语句必须以分号结尾" | 在语句末尾添加 `;` |
| E002 | SQL 语法错误 | "无法解析 SQL 语句，请检查语法" | 检查 SQL 语法，确保语句合法 |
| E003 | 空输入 | "未检测到 SQL 语句" | 输入至少一条合法的 SQL 语句 |
| E004 | 多条 SQL 未用空行分隔 | "多条 SQL 请用空行分隔" | 在 SQL 语句之间添加空行 |
| E005 | 包含非 SQL 内容 | "输入包含非 SQL 内容" | 移除 SQL 之外的其他文本 |
| E006 | 无法确定字段类型 | "字段类型无法确定，已输出占位符" | 检查字段来源，补充必要信息 |

---

## 六、FAQ 反模式对照

### 反模式 1：猜测字段类型

**错误做法**：看到 `created_at` 就推断为 `Date` 类型。

**正确做法**：输出 `[需核实:created_at]`，由用户确认实际类型。

### 反模式 2：假设数据库约束

**错误做法**：看到 `NOT NULL` 就认为字段必填。

**正确做法**：不假设任何约束，全部输出为基础类型。

### 反模式 3：推断业务含义

**错误做法**：看到 `status` 字段就推断为枚举类型。

**正确做法**：输出 `string` 类型，由用户自行定义枚举。

### 反模式 4：忽略错误码

**错误做法**：遇到错误不查错误码表，反复尝试。

**正确做法**：根据错误码定位问题，按修正步骤操作。

### 反模式 5：混合输入

**错误做法**：在 SQL 中混入注释或其他文本。

**正确做法**：保持输入纯净，仅包含 SQL 语句。

---

## 七、渐进式阅读路径

### 速查卡（30 秒上手）

1. 输入以 `;` 结尾的 SQL
2. 多条 SQL 用空行分隔
3. 默认输出 TypeScript 类型
4. 加 `--zod` 输出 Zod 模板
5. 出错查错误码表

### 新手路径（5 分钟掌握）

1. 阅读"能力边界速查卡"了解适用范围
2. 查看"标准执行流程"中的步骤 1-3
3. 对照"错误码体系"处理常见问题
4. 参考"FAQ 反模式对照"避免常见错误

### 进阶路径（深入使用）

1. 理解"置信度门控"的占位符机制
2. 掌握类型映射表的边界情况
3. 熟悉批量处理的输入格式要求
4. 了解 Zod 模板与 TypeScript 类型的差异

---

## 八、使用示例

### 示例 1：基础类型生成

**输入**：
```sql
SELECT id, name, age FROM users;
```

**输出**：
```typescript
export interface QueryResult {
  id: number;
  name: string;
  age: number;
}
```

### 示例 2：聚合函数处理

**输入**：
```sql
SELECT COUNT(*) as total, AVG(age) as avg_age FROM users;
```

**输出**：
```typescript
export interface QueryResult {
  total: number;
  avg_age: number;
}
```

### 示例 3：Zod 模板生成

**输入**：
```bash
bun-sqlgen --zod "SELECT id, name FROM users;"
```

**输出**：
```typescript
import { z } from 'zod';

export const QueryResultSchema = z.object({
  id: z.number(),
  name: z.string(),
});

export type QueryResult = z.infer<typeof QueryResultSchema>;
```

### 示例 4：批量处理

**输入**：
```bash
bun-sqlgen "SELECT id FROM users;
SELECT name, email FROM contacts;"
```

**输出**：
```typescript
export interface QueryResult1 {
  id: number;
}

export interface QueryResult2 {
  name: string;
  email: string;
}
```

---

## 九、命令行接口

| 参数 | 说明 | 示例 |
|------|------|------|
| `--selftest` | 运行自检 | `bun-sqlgen --selftest` |
| `--version` | 显示版本号 | `bun-sqlgen --version` |
| `--zod` | 输出 Zod 模板 | `bun-sqlgen --zod "SQL语句"` |
| 无参数 | 默认输出 TypeScript 类型 | `bun-sqlgen "SQL语句"` |

---

## 用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。包括但不限于因类型定义错误、代码生成偏差导致的任何直接或间接损失。

2. **禁止反向工程**：不得对本 Skill 的输出结果进行反向工程、反编译、反汇编，或试图提取底层算法逻辑。

3. **合规使用**：使用者应确保输入的 SQL 语句不包含敏感信息、商业机密或违反法律法规的内容。

4. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

5. **修改与分发**：使用者可基于本 Skill 进行修改和分发，但需保留原始版权声明。

---

## 许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 TypeForge Studio

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

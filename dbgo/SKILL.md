---
slug: dbgo
name: dbgo
displayName: 数据库消费包 查询优化 Go代码生成
description: 依据库表结构自动产出优化查询语句与Go消费代码。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataFlow Studio
agent_created: true
trigger_words: ["dbgo", "数据库消费包", "SQL生成", "Go代码生成", "查询优化", "数据访问层", "仓储模式"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# dbgo — 数据库消费包自动生成 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入要求 | 输出产物 |
|--------|------|----------|----------|
| 消费包骨架生成 | 基于表结构生成 Go 语言数据访问层代码 | 表结构 DDL 或 ORM 模型文件 | `.go` 文件（含 CRUD 方法） |
| SQL 语句生成 | 生成与 Go 代码配套的 SQL 查询语句 | 表名、字段清单、过滤条件 | `.sql` 文件（含索引建议注释） |
| 查询优化建议 | 分析 WHERE/JOIN/ORDER BY 子句，给出索引与改写建议 | 慢查询日志或 SQL 文本 | 优化报告（Markdown 格式） |
| 批量处理 | 对多张表或多组模型批量生成消费包 | 目录内多个模型文件 | 按表名分目录输出的代码包 |

### 1.2 不能做什么（明确拒绝）

| 场景 | 处理方式 |
|------|----------|
| 无表结构信息（仅有业务描述） | 拒绝生成，提示先提供 DDL 或模型文件 |
| 目标数据库为 Oracle/DB2 等非主流引擎 | 仅生成 ANSI SQL，不生成方言特性代码 |
| 需要事务编排/分布式事务逻辑 | 不生成，仅生成单实体 CRUD |
| 需要鉴权、审计、多租户业务规则 | 不生成，需用户自行在 Service 层补充 |

### 1.3 适用对象

- 使用 Go 1.20+ 开发 REST API 或微服务的后端工程师
- 使用 PostgreSQL / MySQL 8.x 作为主存储的团队
- 需要快速搭建数据访问层（Repository 模式）的敏捷项目

---

## 二、触发方式

### 2.1 触发词

直接使用 `dbgo` 或以下同义场景词触发：

| 触发词 | 典型用户表述 |
|--------|--------------|
| dbgo | “用 dbgo 给 user 表生成消费包” |
| 数据库消费包 | “帮我生成订单表的数据库消费包” |
| SQL生成 | “根据这个模型生成对应的 SQL” |
| Go代码生成 | “把这几张表转成 Go 的 Repository 代码” |
| 查询优化 | “这条 SQL 太慢，帮我看看怎么优化” |

### 2.2 场景映射表

| 用户实际场景 | 触发词示例 | Skill 响应动作 |
|--------------|------------|----------------|
| 新模块开发，需要快速建数据层 | “给 product 表生成 CRUD 代码” | 生成 `product_repo.go` + `product.sql` |
| 已有 SQL 性能差 | “这个 JOIN 查询要 3 秒，优化下” | 输出索引建议 + 改写后的 SQL |
| 批量迁移旧系统数据模型 | “把 legacy 目录下 20 个模型全部生成” | 批量生成并输出汇总清单 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 缺失时的处理 |
|------|------|--------------|
| 输入文件 | DDL 文件（`.sql`）或 Go 结构体文件（`.go`） | 提示“请提供表结构或模型文件” |
| 命名规范 | 表名/结构体名使用 `snake_case` 或 `PascalCase` 一致风格 | 自动识别，不一致时给出警告并统一 |
| 目录结构 | 所有待处理文件位于同一目录 | 提示“请将文件放入同一目录” |

### 3.2 执行步骤（分步编号）

**Step 1 — 输入准备**
- 将待处理文件放入同一目录，确认命名规范一致。
- 若目录内存在多个文件，先列出清单供确认。

**Step 2 — 试运行（单样本）**
- 选取第一个文件执行 `dbgo --selftest`。
- 核对输出字段：表名映射、字段类型转换、SQL 占位符格式。
- 确认无误后进入下一步。

**Step 3 — 批量执行**
- 对全量文件执行生成命令。
- 输出目录结构：`./output/{table_name}/` 下含 `repo.go`、`model.go`、`query.sql`。
- 保留原始文件备份至 `./backup/` 目录。

**Step 4 — 校验结果**
- 抽查 20% 输出条目，核对关键字段（主键、外键、时间字段）与源数据一致。
- 检查 SQL 中 `WHERE` 条件是否与模型 tag 对应。

### 3.3 输出规范

| 输出物 | 命名规则 | 内容要求 |
|--------|----------|----------|
| Go 模型文件 | `{table_name}.go` | 结构体字段与表字段一一对应，含 `json` tag |
| Repository 文件 | `{table_name}_repo.go` | 含 `FindByID`、`FindAll`、`Insert`、`Update`、`Delete` 五个方法 |
| SQL 文件 | `{table_name}.sql` | 含建表语句（如无则省略）、5 条 CRUD 语句、索引建议注释 |
| 优化报告 | `optimization_report.md` | 仅当请求优化时输出，含问题分析、改写前后对比 |

---

## 四、置信度门控

### 4.1 信息不足时的处理

当输入信息不足以生成准确代码时，使用 `[需核实:字段名]` 占位符，**不编造**。

| 缺失信息 | 占位符示例 | 后续处理 |
|----------|------------|----------|
| 主键字段名 | `[需核实:primary_key]` | 提示用户补充 DDL 或模型 tag |
| 字段类型不明确 | `[需核实:field_type_for_created_at]` | 默认按 `time.Time` 处理并标注 |
| 索引需求不明确 | `[需核实:index_on_user_id]` | 不自动加索引，仅注释建议 |

### 4.2 置信度分级

| 置信度 | 判定条件 | 输出行为 |
|--------|----------|----------|
| 高（≥90%） | 输入含完整 DDL 或结构体 tag | 直接生成，无占位符 |
| 中（70%-89%） | 输入含部分字段类型缺失 | 生成代码 + 占位符 + 修正提示 |
| 低（<70%） | 仅有表名无字段信息 | 拒绝生成，要求补充输入 |

---

## 五、错误码体系

| 错误码 | 错误场景 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `E001` | 输入文件不存在 | “未找到指定文件，请检查路径” | 确认路径后重试 |
| `E002` | 文件格式不支持 | “仅支持 .sql 和 .go 文件” | 转换格式后重试 |
| `E003` | 表名与结构体名不一致 | “检测到命名不一致，已按表名优先处理” | 检查命名规范后重新生成 |
| `E004` | 字段类型映射失败 | “字段 `xxx` 类型无法映射，已使用 `interface{}`” | 手动补充类型映射 |
| `E005` | 批量生成中断 | “第 N 个文件处理失败，已跳过并记录日志” | 查看 `error.log` 后单独重试 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正确模式（推荐做法） |
|--------|--------------------|----------------------|
| 忽略试运行直接全量生成 | 直接对 100 个文件执行批量生成，结果字段全错 | 先单样本验证，再批量执行 |
| 不保留原始文件备份 | 生成后覆盖原文件，无法回滚 | 自动备份至 `./backup/` |
| 对无索引字段做 WHERE 查询 | 生成 SQL 不加索引提示，导致慢查询 | 在 SQL 注释中给出 `CREATE INDEX` 建议 |
| 将生成代码直接用于生产 | 不审查直接部署，出现 SQL 注入风险 | 生成代码默认使用参数化查询，但需人工复核 |
| 忽略错误日志 | 批量失败后不查看 `error.log`，重复失败 | 每次失败后先查日志再重试 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 放文件 → 同一目录
2. 试运行 → dbgo --selftest
3. 批量跑 → dbgo
4. 看结果 → ./output/ 目录
```

### 7.2 新手路径（首次使用）

1. 阅读本 Skill 的「能力边界」章节，确认适用场景。
2. 准备一个最小示例（单张表 DDL），按「标准流程」Step 1-2 执行。
3. 查看输出文件，对照「输出规范」核对字段。
4. 确认无误后，再处理全量数据。

### 7.3 进阶路径（熟练用户）

1. 使用 `--optimize` 参数对慢查询进行优化分析。
2. 自定义字段类型映射（通过 `config.yaml` 覆盖默认映射）。
3. 结合 `go generate` 将 dbgo 集成到 CI 流水线。

---

## 八、参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--selftest` | 布尔 | `false` | 单样本试运行模式 |
| `--version` | 布尔 | `false` | 输出版本号 |
| `--optimize` | 布尔 | `false` | 启用查询优化分析 |
| `--output` | 字符串 | `./output` | 输出目录路径 |
| `--backup` | 字符串 | `./backup` | 备份目录路径 |
| `--config` | 字符串 | `./config.yaml` | 自定义配置文件路径 |

---

## 九、用户协议

使用本 Skill 生成的所有代码与 SQL 脚本，**使用者自行承担全部责任**。包括但不限于：代码正确性、安全性、性能表现及合规性。

**禁止反向工程**：不得对本 Skill 的提示词、内部逻辑进行逆向解析、提取或用于商业竞争。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

本 Skill 基于 MIT 许可证开源发布。

```
MIT License

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
```

<!-- professional-license-embedded -->

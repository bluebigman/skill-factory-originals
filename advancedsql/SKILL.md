---
slug: advancedsql
name: advancedsql
displayName: 自然语言转SQL 多方言查询生成
description: 把自然语言或数据文件转成结构化SQL查询，支持多方言适配与优化建议。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林澈
agent_created: true
trigger_words: ["自然语言转SQL", "生成SQL查询", "数据文件转SQL", "SQL方言适配", "SQL优化建议", "advancedsql", "写个查询语句", "把表格转成SQL"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# advancedsql · 自然语言转 SQL 与多方言查询生成

把一句人话、一份 CSV/JSON/Excel 数据文件，转成可直接执行的 SQL 查询语句与结果集；同时给出方言适配与优化建议。适合数据分析、后端开发、报表搭建等需要频繁写查询的场景。

---

## 一、能力边界速查卡（一页纸）

| 维度 | 说明 |
| --- | --- |
| 输入形态 | 自然语言描述、CSV / JSON / Excel / TSV 数据文件、已有 SQL 片段 |
| 输出形态 | 结构化 SQL 语句、结果集预览、方言适配版本、优化建议清单 |
| 支持方言 | MySQL、PostgreSQL、SQLite、SQL Server、Oracle、ClickHouse、Hive |
| 适用对象 | 数据分析师、后端工程师、BI 报表开发者、数据运营 |
| 运行方式 | 命令行 CLI（argparse 参数化），支持自检与干跑预览 |
| 编码支持 | UTF-8 / GBK / GB18030 三级自动回退 |

**能做：**
- 将自然语言意图解析为 SELECT / INSERT / UPDATE / DELETE / CREATE 等语句
- 读取本地数据文件，推断字段类型并生成建表 + 插入语句
- 同一逻辑查询输出多种方言版本
- 给出索引、JOIN 顺序、子查询改写等优化建议
- `--dry-run` 预览将要写盘的内容
- `--selftest` 验证核心函数是否正常

**不能做：**
- 不连接真实数据库执行语句（只生成与预览，不代跑生产库）
- 不替代 DBA 做权限、备份、事务策略决策
- 不保证生成语句在未声明方言上可直接运行
- 不处理加密、脱敏、合规审计等数据治理事务

---

## 二、触发方式与场景映射

`trigger_words`：自然语言转SQL、生成SQL查询、数据文件转SQL、SQL方言适配、SQL优化建议、advancedsql、写个查询语句、把表格转成SQL

| 大白话场景 | 对应能力 |
| --- | --- |
| “帮我把这句话写成查询” | 自然语言 → SQL |
| “这个 CSV 怎么建表” | 数据文件 → DDL + DML |
| “这段 SQL 在 PG 上怎么写” | 方言适配 |
| “这条查询太慢了帮我看看” | 优化建议 |
| “先别写盘，给我看看要生成啥” | `--dry-run` 预览 |
| “跑一下自检确认没坏” | `--selftest` |

---

## 三、标准流程

### 前置条件
- 已安装本 Skill 运行环境（Python 3.9+）
- 输入文件存在且可读；自然语言描述尽量包含表名、字段、过滤条件
- 明确目标方言（未指定时默认 MySQL）

### 执行步骤

1. **确认输入**：整理自然语言描述或数据文件路径，明确目标方言与输出格式。
2. **干跑预览**（推荐）：先执行 `--dry-run`，查看将要生成的 SQL 与写盘路径。
3. **正式执行**：去掉 `--dry-run` 运行，生成 SQL 文件与结果集预览。
4. **检查输出**：核对字段映射、过滤条件、方言关键字是否符合预期。
5. **异常处理**：若报错，按错误码表定位并修正后重跑。

### 常用参数表

| 参数 | 说明 | 默认值 |
| --- | --- | --- |
| `--input` | 输入文件路径或自然语言文本 | 无 |
| `--dialect` | 目标方言（mysql/pg/sqlite/mssql/oracle/clickhouse/hive） | mysql |
| `--output` | 输出 SQL 文件路径 | 当前目录 out.sql |
| `--encoding` | 指定编码，缺省时自动三级回退 | auto |
| `--dry-run` | 仅预览不写盘 | False |
| `--selftest` | 运行自检契约 | False |
| `--version` | 打印版本号 | — |

### 输出规范
- SQL 文件：UTF-8 编码，语句以分号结尾，含注释头（生成时间、方言、来源）
- 结果集预览：以表格形式打印前 N 行（默认 20 行）
- 优化建议：以列表形式输出，每条含“问题 → 建议 → 预期收益方向”

---

## 四、置信度门控

当输入信息不足以确定字段、表名或过滤条件时，**不编造**，统一输出占位符：

```
[需核实:表名] [需核实:字段名] [需核实:过滤条件]
```

示例输出：

```sql
SELECT [需核实:字段名]
FROM [需核实:表名]
WHERE [需核实:过滤条件];
```

用户补齐占位内容后重跑即可。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
| --- | --- | --- | --- |
| E1001 | 输入文件不存在 | 未找到输入文件，请检查路径 | 确认路径拼写与文件权限 |
| E1002 | 编码无法识别 | 文件编码不在支持范围 | 用 `--encoding` 显式指定 |
| E1003 | 方言不支持 | 目标方言不在支持列表 | 从支持列表中选择 |
| E1004 | 字段推断失败 | 无法从数据推断字段类型 | 手动补充字段定义 |
| E1005 | 写盘失败 | 输出路径不可写 | 更换输出目录或检查权限 |
| E1006 | 自检未通过 | 核心函数异常 | 查看自检报告并反馈 |

---

## 六、FAQ 与反模式

**坑 1：描述太模糊**
- 反模式：“帮我查一下数据”
- 正解：“从 orders 表查 2024 年 1 月至今 status=paid 的订单，按金额降序”

**坑 2：忽略方言差异**
- 反模式：把 MySQL 的 `LIMIT` 直接丢给 SQL Server
- 正解：显式指定 `--dialect mssql`，由工具输出 `TOP` 写法

**坑 3：直接写盘不预览**
- 反模式：跳过 `--dry-run` 直接覆盖已有 SQL 文件
- 正解：先干跑确认，再正式执行

**坑 4：编码问题甩锅工具**
- 反模式：GBK 文件报错就认为工具坏了
- 正解：用 `--encoding gbk` 或依赖三级回退，仍失败则转存 UTF-8

**坑 5：把生成结果当生产脚本直接跑**
- 反模式：不审查就执行生成的 DELETE/UPDATE
- 正解：生成后人工复核，尤其是写操作语句

---

## 七、渐进式披露

**新手路径（5 分钟上手）**
1. 读「能力边界速查卡」
2. 跑一次 `--selftest` 确认环境正常
3. 用 `--dry-run` 试一条自然语言转 SQL
4. 去掉 `--dry-run` 正式生成

**进阶路径**
1. 研究「常用参数表」，组合 `--dialect` + `--encoding`
2. 用数据文件生成建表语句，核对字段类型推断
3. 阅读优化建议，理解索引与 JOIN 改写逻辑
4. 按错误码体系建立自己的排错清单

---

## 用户协议

<!-- user-agreement-injected -->

使用本 Skill 即表示您已阅读并同意以下条款：

1. 本 Skill 由 AI 辅助生成，仅供学习与参考，不构成任何专业建议。
2. 使用者需自行承担使用本 Skill 产生的全部责任，包括但不限于生成 SQL 的正确性、执行后果、数据安全与合规风险。
3. 禁止对本 Skill 进行反向工程、反编译、拆解或用于任何违法用途。
4. 生成的 SQL 语句在投入生产环境前，应由使用者自行审查与测试。
5. 本 Skill 不连接、不操作任何真实数据库，不承担因使用者自行执行语句导致的任何损失。

---

## 许可证（License）

<!-- professional-license-embedded -->

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

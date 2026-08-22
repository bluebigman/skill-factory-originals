---
slug: querycsv
name: querycsv
displayName: 表格数据 SQL 查询分析
description: 加载CSV文件，用SQL语句查询、筛选、聚合分析并导出结果。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataCraft Studio
agent_created: true
trigger_words: ["SQL查询", "CSV查询", "表格分析", "数据筛选", "csv转sql", "数据透视", "条件过滤"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# querycsv — CSV 文件 SQL 查询分析工具

## 一、能力边界速查卡

### 1.1 能做什么

| 功能项 | 说明 | 示例 |
|--------|------|------|
| 加载 CSV | 读取指定路径的 CSV 文件，自动识别表头与分隔符 | `load('sales.csv')` |
| SQL 查询 | 支持 SELECT、WHERE、GROUP BY、ORDER BY、JOIN 等标准 SQL 语法 | `SELECT region, SUM(amount) FROM sales GROUP BY region` |
| 数据筛选 | 按条件过滤行记录，支持多条件组合 | `WHERE date >= '2024-01-01' AND amount > 1000` |
| 聚合分析 | 求和、均值、计数、最大/最小值等聚合运算 | `SELECT AVG(price) FROM products` |
| 结果导出 | 将查询结果保存为新 CSV 文件 | `export(result, 'output.csv')` |
| 表连接 | 支持多表 INNER JOIN / LEFT JOIN | `SELECT * FROM a JOIN b ON a.id = b.id` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不支持写入原文件 | 查询操作只读，不修改源 CSV 内容 |
| 不支持复杂事务 | 无事务回滚机制，多步操作需自行管理 |
| 不支持存储过程 | 仅支持单条 SQL 语句或简单脚本序列 |
| 不支持非表格数据 | JSON 嵌套、XML 等非扁平结构需先预处理 |
| 不支持跨文件 JOIN | 仅支持已加载到内存中的表对象 |

### 1.3 适用对象

- 需要快速探查 CSV 数据内容的数据分析初学者
- 需要做临时筛选、统计但不想写 Python/Pandas 的运营人员
- 需要验证数据质量、核对字段一致性的测试工程师
- 需要将 CSV 数据转为可查询结构的数据工程师

---

## 二、触发方式与场景映射

### 2.1 触发词

当用户输入包含以下关键词时，自动激活本 Skill：

| 触发词 | 典型用户表述 |
|--------|-------------|
| SQL查询 | "帮我用 SQL 查一下这个 CSV" |
| CSV查询 | "这个表格文件怎么筛选数据" |
| 表格分析 | "分析一下销售数据的地区分布" |
| 数据筛选 | "把金额大于 500 的行筛出来" |
| csv转sql | "把这个 CSV 转成能查的数据库表" |
| 数据透视 | "按月份汇总一下订单量" |
| 条件过滤 | "只保留状态为已发货的记录" |

### 2.2 场景映射表

| 用户场景 | 实际需求 | 本 Skill 动作 |
|----------|----------|---------------|
| "这个文件有 10 万行，我想看前 100 行" | 快速预览 | `SELECT * FROM data LIMIT 100` |
| "帮我统计每个城市的平均消费" | 分组聚合 | `SELECT city, AVG(spend) FROM data GROUP BY city` |
| "把 3 月份的数据单独存出来" | 条件筛选 + 导出 | `SELECT * FROM data WHERE month = '2024-03'` + export |
| "两个表都有用户 ID，怎么合并查" | 表连接 | `SELECT * FROM t1 JOIN t2 ON t1.uid = t2.uid` |
| "这个 CSV 的列名是什么" | 查看表结构 | `DESCRIBE data` 或 `SELECT * FROM data LIMIT 1` |

---

## 三、标准操作流程

### 3.1 前置条件

| 条件项 | 要求 | 检查方式 |
|--------|------|----------|
| 文件格式 | 标准 CSV（UTF-8 编码，逗号分隔） | 用文本编辑器打开确认 |
| 文件路径 | 文件与 Skill 工作目录一致，或提供绝对路径 | `ls` 查看目录 |
| 表头规范 | 首行必须为列名，且无重复列名 | 查看文件前 3 行 |
| 数据一致性 | 同列数据类型尽量一致（全数字或全文本） | 随机抽查 5 行 |
| 文件大小 | 建议单文件 ≤ 500MB，超过需分片处理 | `ls -lh` 查看 |

### 3.2 执行步骤

**Step 1：加载文件**

```
load('filename.csv')
```

- 若文件不在当前目录，使用完整路径：`load('/data/raw/filename.csv')`
- 加载成功后返回表名（默认取文件名去扩展名），如 `filename`

**Step 2：试运行（单样本验证）**

先执行一条简单查询确认结构：

```
SELECT * FROM filename LIMIT 5
```

核对项：
- 列名是否与预期一致
- 数据类型是否正确（数字列是否为数值）
- 是否有空值或异常字符

**Step 3：编写正式查询**

根据分析目标编写 SQL：

```
SELECT column1, column2, COUNT(*) AS cnt
FROM filename
WHERE condition
GROUP BY column1, column2
ORDER BY cnt DESC
```

**Step 4：执行并检查结果**

- 检查返回行数是否合理（与预期量级一致）
- 抽查 3-5 条记录，与源文件人工比对
- 确认聚合值计算正确（如总和、均值）

**Step 5：导出结果**

```
export(result, 'output_filename.csv')
```

导出规范：
- 文件名建议包含日期或业务标识，如 `sales_summary_20250101.csv`
- 导出文件与源文件放在不同目录，避免覆盖

**Step 6：保留备份**

- 原始 CSV 文件不做任何修改
- 导出结果单独存放，不覆盖源文件

### 3.3 输出规范

| 输出类型 | 格式要求 | 示例 |
|----------|----------|------|
| 查询结果（终端） | 表格形式，列对齐，最多显示 50 行 | 见下方示例 |
| 导出文件 | UTF-8 编码 CSV，含表头 | `output.csv` |
| 错误信息 | 明确错误码 + 原因 + 修正建议 | 见第五节 |

终端输出示例：

```
+---------+--------+-------+
| region  |  total | count |
+---------+--------+-------+
| 华东    | 15230  | 45    |
| 华北    | 9820   | 32    |
| 华南    | 12450  | 38    |
+---------+--------+-------+
3 rows returned
```

---

## 四、置信度门控机制

### 4.1 信息不足时的处理原则

当遇到以下情况时，**不得编造数据或猜测结果**：

| 场景 | 处理方式 | 输出示例 |
|------|----------|----------|
| 列名不确定 | 先执行 `DESCRIBE` 或 `SELECT * LIMIT 1` 确认 | 先查看表结构再查询 |
| 数据值缺失 | 在结果中标记 `[需核实:字段名]` | `[需核实:amount]` |
| 聚合结果异常 | 标注 `[需核实:计算逻辑]` 并检查源数据 | `[需核实:SUM(amount)]` |
| 文件编码不确定 | 先检查文件头，确认 UTF-8 或 GBK | 先执行 `file filename.csv` |
| 表关系不明确 | 输出 `[需核实:关联键]` 并请求用户确认 | `[需核实:JOIN 条件]` |

### 4.2 占位符使用规则

- 格式：`[需核实:具体字段或逻辑]`
- 位置：在结果表格中对应单元格内，或查询说明中
- 用途：提示用户该处数据需要人工确认，不视为最终结果

### 4.3 禁止行为

- 禁止用随机值填充缺失数据
- 禁止假设列名或数据类型
- 禁止在未确认 JOIN 条件时强行关联表

---

## 五、错误码体系

| 错误码 | 错误描述 | 用户提示话术 | 修正步骤 |
|--------|----------|-------------|----------|
| QCSV-001 | 文件不存在 | "未找到指定文件，请检查路径是否正确" | 1. 确认文件名拼写 2. 确认文件在当前目录 3. 使用绝对路径 |
| QCSV-002 | 文件格式错误 | "文件不是有效的 CSV 格式，请检查分隔符和编码" | 1. 用文本编辑器打开确认 2. 确认分隔符为逗号 3. 确认编码为 UTF-8 |
| QCSV-003 | 列名不存在 | "查询中引用的列不存在，请检查列名拼写" | 1. 执行 `DESCRIBE` 查看所有列 2. 核对拼写 3. 确认大小写 |
| QCSV-004 | SQL 语法错误 | "SQL 语句存在语法错误，请检查关键字和括号" | 1. 检查 SELECT/WHERE/GROUP BY 拼写 2. 确认括号匹配 3. 简化语句逐步调试 |
| QCSV-005 | 类型不匹配 | "比较操作中数据类型不一致，请检查字段类型" | 1. 确认数字列不含文本 2. 日期列格式统一 3. 使用 CAST 转换 |
| QCSV-006 | 内存不足 | "文件过大，超出处理能力，请分片处理" | 1. 使用 WHERE 条件分段查询 2. 先筛选再聚合 3. 拆分文件 |
| QCSV-007 | 导出失败 | "导出文件失败，请检查目标目录权限" | 1. 确认目录可写 2. 更换导出路径 3. 检查磁盘空间 |
| QCSV-008 | 空结果集 | "查询结果为空，请检查筛选条件" | 1. 确认条件值正确 2. 放宽条件测试 3. 检查数据是否为空 |

---

## 六、FAQ 反模式对照

### 6.1 常见坑与正确做法

| 常见错误（反模式） | 问题说明 | 正确做法 |
|-------------------|----------|----------|
| 直接对全量数据执行复杂查询 | 大文件可能超时或内存溢出 | 先用 LIMIT 或 WHERE 缩小范围测试 |
| 忽略列名大小写 | 某些系统区分大小写，导致列找不到 | 先 DESCRIBE 确认实际列名 |
| 混合类型列直接聚合 | 文本列做 SUM 会报错或结果异常 | 先确认列类型，必要时用 CAST |
| 导出文件覆盖源文件 | 误操作导致原始数据丢失 | 导出到独立目录，文件名加时间戳 |
| 多表 JOIN 不指定关联键 | 产生笛卡尔积，结果行数爆炸 | 始终明确 ON 条件，先小数据量验证 |
| 忽略空值处理 | NULL 参与计算导致结果偏差 | 用 IS NULL / IS NOT NULL 显式处理 |
| 一次查询做太多事 | 难以定位错误，调试困难 | 拆分为多个简单查询逐步验证 |

### 6.2 反模式对照表

| 反模式 | 反例 | 正例 |
|--------|------|------|
| 无验证批量执行 | "直接跑全量，出结果再说" | "先 LIMIT 10 验证，再全量执行" |
| 忽略备份 | "原文件不用管，直接覆盖" | "导出到 backup 目录，保留源文件" |
| 猜测列名 | "应该是 amount 列，直接查" | "先 DESCRIBE 确认列名" |
| 跳过抽查 | "结果看着对就行" | "随机抽 5 条与源文件比对" |
| 不处理异常 | "报错就重试，不行就换工具" | "根据错误码定位原因，针对性修正" |

---

## 七、渐进式披露指南

### 7.1 速查卡（30 秒上手）

```
1. 加载：load('file.csv')
2. 预览：SELECT * FROM file LIMIT 5
3. 查询：SELECT ... WHERE ... GROUP BY ...
4. 导出：export(result, 'out.csv')
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界速查卡」了解工具范围
2. 按「标准操作流程」Step 1-2 完成文件加载和预览
3. 参考「场景映射表」找到自己的需求类型
4. 使用简单 SELECT + WHERE 完成第一次筛选
5. 遇到问题查「错误码体系」定位并修正

### 7.3 进阶路径（熟练用户）

1. 掌握 GROUP BY + 聚合函数进行统计分析
2. 使用 JOIN 实现多表关联查询
3. 结合子查询处理复杂筛选逻辑
4. 利用「置信度门控」机制处理数据质量问题
5. 批量处理多个文件时，先单样本验证再全量执行

### 7.4 专家路径（深度使用）

1. 组合多个查询步骤构建分析流水线
2. 使用 CASE WHEN 实现条件逻辑
3. 通过窗口函数（如 ROW_NUMBER）实现排名分析
4. 自定义导出格式，对接下游系统
5. 建立文件命名与备份规范，形成可复用流程

---

## 八、参数参考表

### 8.1 常用 SQL 操作

| 操作 | 语法 | 示例 |
|------|------|------|
| 条件筛选 | WHERE | `WHERE status = 'active'` |
| 排序 | ORDER BY | `ORDER BY amount DESC` |
| 分组 | GROUP BY | `GROUP BY region` |
| 聚合 | COUNT/SUM/AVG | `SELECT COUNT(*) FROM t` |
| 去重 | DISTINCT | `SELECT DISTINCT city FROM t` |
| 限制行数 | LIMIT | `LIMIT 100` |
| 模糊匹配 | LIKE | `WHERE name LIKE '张%'` |
| 范围筛选 | BETWEEN | `WHERE date BETWEEN '2024-01-01' AND '2024-12-31'` |
| 多条件 | AND/OR | `WHERE a > 10 AND b < 20` |
| 空值判断 | IS NULL | `WHERE email IS NOT NULL` |

### 8.2 边界值建议

| 参数 | 建议值 | 说明 |
|------|--------|------|
| 单次查询最大行数 | 100,000 行 | 超过建议分片 |
| 预览默认行数 | 5-10 行 | 快速确认结构 |
| 导出文件大小 | ≤ 200MB | 超过建议压缩或分片 |
| 多表 JOIN 数量 | ≤ 3 张表 | 超过建议分步处理 |
| 单条 SQL 长度 | ≤ 2000 字符 | 超过建议拆分 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用须知：**

1. 本 Skill 仅提供数据处理辅助功能，使用者应自行对操作结果负责。
2. 使用者确认已理解：任何数据查询、分析、导出操作均可能产生不可预期的结果，使用者应自行验证输出数据的准确性与完整性。
3. 使用者承诺：不将本 Skill 用于任何违反法律法规或侵犯第三方权益的用途。
4. 禁止对本 Skill 进行反向工程、反编译、破解或试图获取其底层实现逻辑。
5. 本 Skill 不提供任何明示或暗示的担保，包括但不限于适销性、特定用途适用性。
6. 因使用本 Skill 产生的任何直接或间接损失，Skill 作者及发布方不承担任何责任。
7. 使用者应妥善保管数据文件，因操作失误导致的数据丢失或损坏，由使用者自行承担。
8. 本协议条款的解释权归 Skill 作者所有，使用者继续使用即视为接受全部条款。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2025 DataCraft Studio

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证功能适用性。*

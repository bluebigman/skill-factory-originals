---
slug: sqlsmith
name: sqlsmith
displayName: SQL查询 数据库操作 语句生成
description: 面向SQL查询与数据库操作的规范化处理技能，提供可复用的流程与输出。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: QueryCraft Studio
agent_created: true
trigger_words: ["SQL查询", "数据库", "sqlsmith", "SQL生成", "数据检索"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# SQLSmith 技能文档

## 一、能力边界速查卡

### 1.1 能做（核心能力）

| 编号 | 能力项 | 说明 | 适用场景示例 |
|------|--------|------|--------------|
| C1 | 结构化转换 | 将用户提供的数据/文件/URL 内容转换为结构化查询结果 | 从 CSV 文件提取数据并生成查询语句 |
| C2 | 关键信息识别 | 识别并保留输入中的关键字段、条件、排序要求 | 从自然语言描述中提取 WHERE 条件 |
| C3 | 约定格式输出 | 按预定义格式生成查询结果或 SQL 语句 | 生成标准 SELECT 语句 |
| C4 | 置信度标注 | 对不确定的字段或推断结果给出置信度提示 | 标注字段映射的置信度百分比 |
| C5 | 批量处理 | 支持多文件、多查询的批量处理和自定义格式输出 | 批量生成 INSERT 语句 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行实际数据库操作 | 本技能仅生成 SQL 语句，不连接真实数据库执行 |
| L2 | 不处理二进制大文件 | 超过 10MB 的二进制文件不在处理范围内 |
| L3 | 不保证语法兼容性 | 生成的 SQL 基于标准语法，特定数据库方言需自行调整 |
| L4 | 不处理敏感数据 | 涉及密码、密钥等敏感信息的输入将直接拒绝处理 |

### 1.3 适用对象

- 需要快速生成 SQL 查询语句的开发人员
- 需要将结构化数据转换为 SQL 操作的学习者
- 需要批量生成数据库操作语句的运维人员

---

## 二、触发方式与场景映射

### 2.1 触发词表

| 触发词 | 同义场景词 | 触发示例 |
|--------|------------|----------|
| SQL查询 | 数据检索、查询语句 | "帮我写一个 SQL 查询" |
| 数据库 | 数据仓库、DBMS | "这个数据库怎么查" |
| sqlsmith | SQL生成器、查询助手 | "用 sqlsmith 处理" |
| SQL生成 | 语句生成、查询构造 | "生成一条查询语句" |
| 数据检索 | 数据提取、信息查询 | "从这些数据中检索信息" |

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 本技能响应 |
|------------------|----------|------------|
| "把这个 Excel 变成 SQL" | 将表格数据转换为 INSERT 语句 | 解析表格结构，生成批量 INSERT |
| "查一下用户表里 30 岁以上的" | 生成带条件的 SELECT 语句 | 生成 WHERE age > 30 的查询 |
| "这个 URL 里的数据怎么查" | 从 URL 指向的数据源提取信息 | 解析 URL 内容，生成查询语句 |
| "批量生成更新语句" | 批量 UPDATE 操作 | 按模板批量生成 UPDATE 语句 |

---

## 三、标准处理流程

### 3.1 前置条件

| 条件项 | 要求 | 检查方式 |
|--------|------|----------|
| 输入格式 | 支持文本、CSV、JSON、URL | 文件扩展名或内容格式识别 |
| 命名规范 | 文件命名需包含表名或业务标识 | 正则匹配 `^[a-z_][a-z0-9_]*\.(csv\|json\|txt)$` |
| 环境要求 | 无需特殊环境，纯文本处理 | 无 |

### 3.2 执行步骤

**Step 1：输入解析**
- 读取输入内容，识别数据类型（文本/CSV/JSON/URL）
- 提取关键字段：表名、列名、条件、排序字段
- 输出：结构化中间表示（JSON 格式）

**Step 2：规则处理**
- 按以下优先级处理规则：
  1. 字段映射规则（输入字段 → 数据库列名）
  2. 条件转换规则（自然语言 → SQL 条件）
  3. 格式规范规则（输出格式标准化）
- 对每个字段标注置信度：
  - 高置信度（≥90%）：字段名完全匹配
  - 中置信度（70-89%）：字段名部分匹配
  - 低置信度（<70%）：字段名推断

**Step 3：结果生成**
- 按约定格式生成 SQL 语句
- 包含必要的注释说明
- 标注不确定字段

**Step 4：自查校验**
- 字段完整性：所有必需字段是否齐全
- 格式正确性：SQL 语法是否符合标准
- 置信度标注：所有推断字段是否标注

### 3.3 输出规范

```sql
-- 生成时间: YYYY-MM-DD HH:MM:SS
-- 置信度: 整体置信度 XX%
-- 生成规则: 版本号

SELECT column1, column2, ...
FROM table_name
WHERE condition1 AND condition2
ORDER BY column1 [ASC|DESC];

-- 字段说明:
-- column1: 说明 [置信度: 95%]
-- column2: 说明 [置信度: 80%]
```

---

## 四、置信度门控机制

### 4.1 置信度等级定义

| 等级 | 置信度范围 | 含义 | 处理方式 |
|------|------------|------|----------|
| 高 | 90-100% | 字段或条件完全确定 | 直接使用 |
| 中 | 70-89% | 字段或条件基本确定 | 使用并提示 |
| 低 | 50-69% | 字段或条件不确定 | 使用并标注 [需核实] |
| 极低 | <50% | 无法确定 | 拒绝生成，请求确认 |

### 4.2 占位符规范

当信息不足时，使用以下占位符：

| 占位符 | 含义 | 示例 |
|--------|------|------|
| `[需核实:字段名]` | 字段名不确定 | `SELECT [需核实:用户ID] FROM users` |
| `[需核实:条件]` | 条件不确定 | `WHERE [需核实:创建时间] > '2024-01-01'` |
| `[需核实:表名]` | 表名不确定 | `FROM [需核实:用户表]` |

### 4.3 禁止行为

- 禁止编造不存在的字段名
- 禁止猜测表结构
- 禁止在低置信度时直接生成最终 SQL

---

## 五、错误码体系

### 5.1 错误码表

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 输入格式不支持 | "无法识别输入格式，请提供文本、CSV、JSON 或 URL" | 1. 检查文件格式 2. 转换为支持的格式 3. 重新提交 |
| E002 | 关键字段缺失 | "缺少必要的表名或列名信息" | 1. 补充表名 2. 补充列名 3. 重新提交 |
| E003 | 置信度过低 | "字段置信度低于 50%，无法生成可靠 SQL" | 1. 提供更多上下文 2. 明确字段映射 3. 重新提交 |
| E004 | 批量处理中断 | "批量处理在第 N 条记录时中断" | 1. 检查第 N 条记录 2. 修正格式 3. 从断点继续 |
| E005 | 输出格式冲突 | "自定义输出格式与标准格式冲突" | 1. 检查自定义格式 2. 调整冲突项 3. 重新生成 |

### 5.2 错误处理流程

```
检测到错误 → 记录错误码 → 生成提示话术 → 提供修正步骤 → 等待用户确认 → 重新处理
```

---

## 六、FAQ 反模式对照

### 6.1 常见坑与反模式

| 编号 | 常见坑 | 反模式示例 | 正确做法 |
|------|--------|------------|----------|
| F1 | 忽略字段类型 | 将字符串字段直接用于数值比较 | 先确认字段类型，再生成条件 |
| F2 | 过度依赖默认值 | 未指定排序时默认使用主键排序 | 明确指定排序字段，或标注默认排序 |
| F3 | 忽略大小写敏感性 | 未考虑数据库大小写敏感设置 | 生成时统一使用小写，并提示用户 |
| F4 | 批量处理不检查 | 直接对全量数据执行未验证的模板 | 先单条验证，再批量执行 |
| F5 | 忽略 NULL 值处理 | 未考虑字段可能为 NULL 的情况 | 在条件中显式处理 NULL 值 |

### 6.2 反模式对照表

| 反模式 | 问题描述 | 正确模式 | 示例 |
|--------|----------|----------|------|
| 直接拼接 | 用户输入直接拼入 SQL | 参数化查询 | `WHERE id = ?` 而非 `WHERE id = 1` |
| 忽略转义 | 特殊字符未转义 | 使用转义函数 | `WHERE name = 'O\'Brien'` |
| 无限制查询 | 未加 LIMIT 的全表查询 | 添加 LIMIT 限制 | `SELECT * FROM users LIMIT 100` |

---

## 七、渐进式披露路径

### 7.1 速查卡（30 秒上手）

```
1. 准备输入文件（CSV/JSON/文本）
2. 调用技能，提供文件路径或内容
3. 获取结构化 SQL 输出
4. 检查置信度标注
5. 手动验证关键字段
```

### 7.2 新手路径（5 分钟掌握）

1. 阅读「能力边界速查卡」了解基本功能
2. 查看「触发方式与场景映射」明确使用场景
3. 按「标准处理流程」执行一次完整操作
4. 遇到问题参考「错误码体系」解决
5. 查看「FAQ 反模式对照」避免常见错误

### 7.3 进阶路径（深度使用）

1. 掌握「置信度门控机制」的细节
2. 自定义输出格式（需符合规范）
3. 批量处理大型数据集
4. 结合其他工具进行数据验证
5. 根据实际需求调整处理规则

---

## 八、批量处理指南

### 8.1 准备阶段

1. **文件组织**：将待处理文件放入同一目录，命名规范为 `[表名]_[日期].[格式]`
2. **模板确认**：确认输出模板与字段映射表
3. **环境检查**：确认输入文件格式正确，无损坏文件

### 8.2 试运行阶段

1. 选择单个样本文件执行
2. 核对输出字段与格式是否符合预期
3. 检查置信度标注是否合理
4. 确认无误后进入批量阶段

### 8.3 批量执行阶段

1. 对全量数据执行处理
2. 保留原始文件备份（自动创建 `backup_YYYYMMDD` 目录）
3. 实时监控处理进度
4. 记录处理日志

### 8.4 校验阶段

1. 抽查输出条目（建议 10% 样本）
2. 核对关键字段与源数据一致性
3. 检查格式规范符合性
4. 生成校验报告

---

## 九、参数配置表

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `input_format` | string | auto | 输入格式（auto/csv/json/text/url） |
| `output_format` | string | sql | 输出格式（sql/json/text） |
| `confidence_threshold` | number | 0.7 | 置信度阈值（0-1） |
| `batch_size` | number | 100 | 批量处理大小 |
| `preserve_case` | boolean | false | 是否保留大小写 |
| `null_handling` | string | explicit | NULL 处理方式（explicit/ignore/error） |
| `max_file_size` | number | 10 | 最大文件大小（MB） |

---

## 十、用户协议

<!-- user-agreement-injected -->

**使用本技能即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本技能产生的全部责任。本技能仅提供 SQL 语句生成与查询辅助功能，不包含任何实际数据库操作。

2. **禁止反向工程**：禁止对本技能进行反向工程、反编译、破解或试图提取源代码。

3. **合法使用**：使用者应确保使用本技能的行为符合当地法律法规，不得用于任何非法用途。

4. **无担保声明**：本技能按"原样"提供，不附带任何明示或暗示的担保。

5. **数据安全**：使用者应自行负责输入数据的合规性与安全性，本技能不存储任何用户数据。

---

## 十一、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 QueryCraft Studio

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

## 十二、版本记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0.0 | 2024-01-01 | 初始版本发布 |

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*

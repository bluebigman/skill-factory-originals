---
slug: sql-query-generator
name: sql-query-generator
displayName: 自然语言转SQL 查询构建器
description: 将自然语言或数据文件转换为可执行SQL查询语句，支持无模式数据源。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: QueryForge Studio
agent_created: true
trigger_words: ["SQL查询", "查询生成", "sql builder", "无模式查询", "自然语言转SQL", "--selftest", "--version", "写SQL", "生成查询语句", "数据查询"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

# 自然语言转SQL 查询构建器（sql-query-generator）

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 自然语言转SQL | 将中文/英文描述转换为标准SQL语句 | "查最近7天订单量" → `SELECT COUNT(*) FROM orders WHERE order_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY);` |
| 无模式数据源适配 | 对没有预定义schema的数据文件（CSV/JSON/Excel）自动推断字段类型与表结构 | 读取CSV表头自动建表 |
| 多方言支持 | 输出MySQL、PostgreSQL、SQLite、SQL Server等方言 | 通过参数指定方言 |
| 数据文件预处理 | 自动识别分隔符、编码、空值处理策略 | 检测到GBK编码自动转UTF-8 |
| 查询优化建议 | 对生成的SQL给出索引、分页、缓存等优化提示 | 大表查询自动建议LIMIT |

### 1.2 不能做什么（明确拒绝）

| 限制项 | 说明 |
|--------|------|
| 不执行SQL | 只生成语句，不连接数据库执行 |
| 不修改数据 | 不生成INSERT/UPDATE/DELETE（除非显式要求） |
| 不处理敏感数据 | 不处理包含身份证号、银行卡号等PII的数据文件 |
| 不支持复杂ETL | 多表JOIN超过5张表时建议拆分 |
| 不保证语法100%正确 | 生成结果需人工复核（见置信度门控） |

### 1.3 适用对象

- **数据分析师**：快速将业务问题转为查询语句
- **后端开发者**：从需求文档提取查询逻辑
- **产品经理**：验证数据可行性，生成临时查询
- **运维人员**：日志数据探索性查询

---

## 二、触发方式与场景映射

### 2.1 触发词表

| 触发词 | 场景示例 |
|--------|----------|
| "SQL查询" | "帮我写个SQL查询，统计每个城市的用户数" |
| "查询生成" | "根据这个CSV生成查询语句" |
| "sql builder" | "Use sql builder to create a query for sales data" |
| "无模式查询" | "这个文件没有表结构，帮我生成查询" |
| "自然语言转SQL" | "把这句话转成SQL：找出库存不足的商品" |
| "写SQL" | "写SQL查一下上个月退款订单" |
| "生成查询语句" | "生成查询语句，按部门分组统计薪资" |
| "数据查询" | "帮我查一下这个Excel里的数据" |

### 2.2 大白话场景映射

| 用户说 | Skill理解 | 执行动作 |
|--------|-----------|----------|
| "这个CSV怎么查？" | 无模式数据源 | 自动推断schema → 生成建表语句 → 生成查询 |
| "把需求转成SQL" | 自然语言转SQL | 解析语义 → 映射字段 → 生成SQL |
| "帮我查一下..." | 查询生成 | 提取查询条件 → 生成SELECT语句 |
| "用sql builder..." | 工具调用 | 进入交互式构建模式 |

---

## 三、标准流程：从输入到输出

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 输入文件 | 与Skill同目录，命名含字母/数字/下划线 | `ls` 确认文件存在 |
| 文件格式 | CSV/JSON/Excel（.xlsx/.xls） | `file` 命令检查 |
| 编码 | UTF-8（非UTF-8自动转换） | `file -i` 查看 |
| 数据量 | 单文件≤100MB，行数≤100万 | `wc -l` 检查 |
| 环境 | Python 3.8+，已安装pandas | `python3 -V` |

### 3.2 执行步骤

#### Step 1：输入准备
```
输入方式A（自然语言）：
  用户直接输入查询描述，如："统计2024年每个月的销售总额，按月份升序"

输入方式B（数据文件）：
  将文件放入当前目录，命名如：sales_data.csv
  执行：python3 sql_gen.py --file sales_data.csv --query "按月统计销售额"
```

#### Step 2：试运行（单样本验证）
```bash
# 使用 --sample 参数仅处理前10行
python3 sql_gen.py --file sales_data.csv --query "按月统计销售额" --sample 10

# 预期输出：
-- 推断的schema:
CREATE TABLE sales_data (
  order_id INT,
  order_date DATE,
  amount DECIMAL(10,2),
  region VARCHAR(50)
);

-- 生成的SQL:
SELECT DATE_FORMAT(order_date, '%Y-%m') AS month, SUM(amount) AS total_sales
FROM sales_data
GROUP BY DATE_FORMAT(order_date, '%Y-%m')
ORDER BY month ASC;
```

#### Step 3：批量执行（全量数据）
```bash
# 确认无误后，去掉 --sample 执行
python3 sql_gen.py --file sales_data.csv --query "按月统计销售额" --output result.sql

# 备份原始文件
cp sales_data.csv sales_data_backup_$(date +%Y%m%d).csv
```

#### Step 4：校验结果
```bash
# 抽查输出SQL，核对：
# 1. 字段名与源数据一致
# 2. 聚合函数使用正确
# 3. 日期格式匹配
# 4. 表名与文件名对应

# 使用 --validate 参数自动检查
python3 sql_gen.py --file sales_data.csv --query "按月统计销售额" --validate
```

### 3.3 输出规范

| 输出项 | 格式 | 示例 |
|--------|------|------|
| Schema推断 | `CREATE TABLE ...` 语句 | 见上 |
| SQL查询 | 标准SQL，缩进清晰 | 见上 |
| 方言适配 | 根据 `--dialect` 参数 | `--dialect postgresql` |
| 优化建议 | 注释形式附在SQL后 | `-- 建议: 在order_date上建索引` |
| 错误提示 | 标准错误码 | `ERR_001: 文件不存在` |

---

## 四、置信度门控

### 4.1 信息不足时的处理

当输入信息不足以生成准确SQL时，使用 `[需核实:字段]` 占位，绝不编造。

| 场景 | 处理方式 | 示例 |
|------|----------|------|
| 字段名不确定 | 输出 `[需核实:字段名]` | `SELECT [需核实:用户ID], name FROM users;` |
| 表关系不明确 | 输出 `[需核实:JOIN条件]` | `SELECT * FROM a JOIN b ON [需核实:关联字段];` |
| 聚合粒度模糊 | 输出 `[需核实:分组维度]` | `GROUP BY [需核实:时间粒度]` |
| 过滤条件缺失 | 输出 `[需核实:时间范围]` | `WHERE order_date > [需核实:起始日期]` |

### 4.2 置信度等级

| 等级 | 说明 | 输出标记 |
|------|------|----------|
| 高（≥90%） | 所有字段/条件明确 | 无标记 |
| 中（70-89%） | 部分字段需确认 | `[需核实:xxx]` |
| 低（<70%） | 关键信息缺失 | 拒绝生成，要求补充信息 |

### 4.3 强制复核清单

生成SQL后，自动附加以下检查项：

```
-- 复核清单：
-- [ ] 所有字段名拼写正确
-- [ ] 表名与文件名/数据库表对应
-- [ ] 日期格式与源数据一致
-- [ ] 聚合函数与分组字段匹配
-- [ ] 无 [需核实] 占位符残留
```

---

## 五、错误码体系

### 5.1 错误码速查表

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `ERR_001` | 文件不存在 | "未找到指定文件，请检查路径" | 1. `ls` 查看当前目录 2. 确认文件名拼写 |
| `ERR_002` | 文件格式不支持 | "仅支持CSV/JSON/Excel格式" | 1. 转换格式 2. 使用 `--format` 指定 |
| `ERR_003` | 编码无法识别 | "无法识别文件编码，请指定" | 1. 使用 `--encoding` 参数 2. 如 `--encoding gbk` |
| `ERR_004` | 字段名冲突 | "检测到重复字段名" | 1. 查看 `--show-schema` 2. 重命名冲突字段 |
| `ERR_005` | 查询语义模糊 | "查询条件不明确，请补充" | 1. 细化查询描述 2. 使用 `--clarify` 交互模式 |
| `ERR_006` | 方言不支持 | "不支持的SQL方言" | 1. 查看 `--list-dialects` 2. 选择支持的方言 |
| `ERR_007` | 数据量超限 | "文件超过100MB限制" | 1. 分割文件 2. 使用 `--chunk-size` 分块处理 |
| `ERR_008` | 生成失败 | "SQL生成失败，请检查输入" | 1. 查看详细日志 `--debug` 2. 简化查询描述 |

### 5.2 错误处理流程

```
遇到错误 → 查看错误码 → 按提示修正 → 重新执行
     ↓
  无法解决 → 使用 --debug 获取详细日志 → 反馈给开发者
```

---

## 六、FAQ 反模式对照

### 6.1 常见坑与反模式

| # | 常见坑 | 反模式（错误做法） | 正确做法 |
|---|--------|-------------------|----------|
| 1 | 忽略schema推断 | 直接使用猜测的字段名 | 先运行 `--show-schema` 确认字段 |
| 2 | 不备份原始文件 | 直接覆盖源文件 | 执行前 `cp` 备份 |
| 3 | 跳过试运行 | 直接全量执行 | 先用 `--sample 10` 验证 |
| 4 | 忽略方言差异 | 用MySQL语法跑PostgreSQL | 指定 `--dialect` 参数 |
| 5 | 不检查空值 | 空值导致聚合结果错误 | 使用 `--handle-null` 参数 |
| 6 | 过度依赖自动生成 | 不人工复核SQL | 按复核清单逐项检查 |
| 7 | 忽略性能提示 | 大表无LIMIT查询 | 采纳优化建议添加LIMIT |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| "直接生成，不用检查" | 字段错误率高 | 先看schema再生成 |
| "一次跑完所有数据" | 出错难定位 | 分批处理+试运行 |
| "SQL能跑就行" | 性能差 | 参考优化建议 |
| "所有表都JOIN" | 查询复杂难维护 | 拆分为多个简单查询 |

---

## 七、渐进式披露：分层次阅读路径

### 7.1 速查卡（30秒上手）

```
1. 放文件 → 2. 写查询 → 3. 试运行 → 4. 全量跑 → 5. 校验
   ↓          ↓          ↓          ↓          ↓
  ls确认    "查..."   --sample 10  去sample   --validate
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」了解能做什么
2. 按「标准流程」Step 1-2 完成一次试运行
3. 遇到问题查「错误码体系」
4. 完成后阅读「FAQ反模式」避免常见坑

### 7.3 进阶路径（熟练用户）

1. 掌握 `--dialect`、`--handle-null` 等高级参数
2. 理解「置信度门控」的占位符处理
3. 自定义schema映射（`--schema-map` 参数）
4. 批量处理多个文件（`--batch` 模式）

### 7.4 参数速查表

| 参数 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `--file` | 输入文件路径 | 无 | `--file data.csv` |
| `--query` | 自然语言查询描述 | 无 | `--query "按月统计"` |
| `--dialect` | SQL方言 | mysql | `--dialect postgresql` |
| `--sample` | 试运行行数 | 无 | `--sample 10` |
| `--output` | 输出文件 | 标准输出 | `--output result.sql` |
| `--validate` | 自动校验 | 关闭 | `--validate` |
| `--show-schema` | 显示推断的schema | 关闭 | `--show-schema` |
| `--handle-null` | 空值处理策略 | skip | `--handle-null fill_zero` |
| `--encoding` | 文件编码 | utf-8 | `--encoding gbk` |
| `--debug` | 调试模式 | 关闭 | `--debug` |
| `--list-dialects` | 列出支持的方言 | 关闭 | `--list-dialects` |
| `--selftest` | 自检功能 | 关闭 | `--selftest` |
| `--version` | 版本信息 | 关闭 | `--version` |

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于：生成的 SQL 语句正确性、数据文件处理结果、以及由此引发的任何直接或间接损失。

2. **禁止反向工程**：不得对本 Skill 的源代码、算法、逻辑进行反向工程、反编译、破解或试图提取底层设计。

3. **合规使用**：使用者应确保使用场景符合当地法律法规，不得用于处理敏感数据（如个人隐私、金融信息、医疗记录等）除非获得相应授权。

4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

5. **修改与分发**：允许修改和再分发，但须保留原始版权声明，并在分发时注明修改内容。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 QueryForge Studio

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*

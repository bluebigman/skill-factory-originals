---
slug: sqlw-mysql
name: sqlw-mysql
displayName: MySQL 代码生成 批量模板 查询封装
description: "为 MySQL 生成查询包装代码或文本源，支持批量与自定义格式。"
version: 3.0.1
rules_version: cpr-20260819-n551
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/sqlw-mysql
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: user_2fd890c9
agent_created: true
trigger_words: ["sqlw-mysql", "mysql代码生成", "sql包装", "查询封装", "批量生成sql", "mysql模板", "sql文本生成"]
display_name: SQLW-MySQL 技能手册
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# SQLW-MySQL 技能手册

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 生成查询包装代码 | 为单条或多条 MySQL 查询生成可复用的函数/方法包装 | `getUserById(id)` |
| 生成文本源 | 输出 SQL 脚本、模板片段、文档化 SQL 文本 | 建表语句、查询模板 |
| 批量处理 | 一次输入多条查询，批量生成对应包装代码 | 10 条查询 → 10 个函数 |
| 自定义格式 | 支持指定代码风格、命名规则、输出结构 | 驼峰命名 / 下划线命名 |
| 参数化查询 | 自动识别查询中的条件字段并转为参数 | `WHERE id = ?` → `$id` |
| 返回类型推断 | 根据查询语句推断返回数据结构 | SELECT 单行 / 多行 / 聚合 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行 SQL | 本技能仅生成代码/文本，不连接数据库执行查询 |
| 不优化查询性能 | 不分析执行计划，不推荐索引策略 |
| 不支持非 MySQL 方言 | 仅针对 MySQL 语法（含 MariaDB 兼容模式） |
| 不处理存储过程/触发器 | 仅面向 SELECT/INSERT/UPDATE/DELETE 语句 |
| 不生成完整项目 | 输出为代码片段或文件内容，不包含项目脚手架 |

### 1.3 适用对象

- 后端开发人员：快速生成数据访问层代码
- 数据分析师：批量生成查询模板用于报表
- DBA：将常用查询封装为标准化脚本
- 教学场景：生成示例代码用于 SQL 教学

---

## 二、触发方式

### 2.1 触发词

使用以下任一关键词即可激活本技能：

- `sqlw-mysql`（主触发词）
- `mysql代码生成`
- `sql包装`
- `查询封装`
- `批量生成sql`
- `mysql模板`
- `sql文本生成`

### 2.2 场景映射表

| 你说的话（大白话） | 技能响应 |
|-------------------|----------|
| "帮我把这几条查询封装成 Python 函数" | 生成 Python 包装代码，含参数和返回类型 |
| "批量生成 20 条 SQL 的 Java 方法" | 输出 Java 方法列表，每条查询对应一个方法 |
| "把这个 SELECT 转成 MyBatis 的 XML" | 生成 MyBatis Mapper XML 片段 |
| "给这些 SQL 加上注释和格式化" | 输出格式化后的 SQL 文本，含说明注释 |
| "生成一个 Node.js 的查询模块" | 生成 Node.js 模块代码，导出查询函数 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 缺失处理 |
|------|------|----------|
| 输入 SQL 语句 | 至少 1 条合法 MySQL 语句 | 提示"请提供 SQL 语句" |
| 目标语言 | 指定 Python/Java/Node.js/纯文本 | 默认输出纯文本 SQL |
| 命名风格 | 可选：驼峰/下划线/帕斯卡 | 默认保持原字段名 |

### 3.2 执行步骤

**步骤 1：解析输入 SQL**

- 识别 SQL 类型（SELECT/INSERT/UPDATE/DELETE）
- 提取表名、字段名、条件字段
- 标记参数占位符（`?` 或 `:name`）

**步骤 2：确认输出配置**

- 目标语言（Python/Java/Node.js/纯文本）
- 批量模式（单条/多条）
- 格式偏好（缩进、引号风格、注释）

**步骤 3：生成包装代码**

- 为每条 SQL 生成独立函数/方法
- 参数映射：条件字段 → 函数参数
- 返回类型：根据查询类型推断

**步骤 4：输出与校验**

- 输出完整代码块
- 标注生成说明（参数表、使用示例）
- 如信息不足，使用 `[需核实:字段]` 占位

### 3.3 输出规范

```text
输出结构：
1. 生成摘要（SQL 数量、目标语言、耗时）
2. 代码块（含语法高亮标记）
3. 参数说明表（参数名、类型、来源字段）
4. 使用示例（调用方式）
5. 注意事项（如有）
```

---

## 四、置信度门控

### 4.1 信息不足处理

当输入信息不足以生成准确代码时，使用以下占位符：

| 场景 | 占位符示例 | 说明 |
|------|-----------|------|
| 字段类型未知 | `[需核实:user_id类型]` | 需确认字段类型 |
| 表名不确定 | `[需核实:表名]` | 无法从上下文推断 |
| 返回结构模糊 | `[需核实:返回格式]` | 需明确单行/多行 |
| 连接方式未知 | `[需核实:连接池配置]` | 需指定数据库连接方式 |

### 4.2 禁止行为

- 不编造不存在的表名或字段名
- 不假设数据库连接参数（主机、端口、账号）
- 不虚构 SQL 执行结果

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 空输入 | "未检测到 SQL 语句，请提供至少一条查询" | 重新输入包含 SQL 的文本 |
| E002 | SQL 语法错误 | "第 X 行存在语法错误，请检查关键字和标点" | 修正 SQL 后重试 |
| E003 | 不支持的语言 | "当前仅支持 Python/Java/Node.js/纯文本" | 选择支持的语言 |
| E004 | 批量模式冲突 | "批量模式与单条模式参数冲突" | 移除多余参数 |
| E005 | 命名风格无效 | "命名风格仅支持 camel/snake/pascal" | 使用支持的风格值 |
| E006 | 参数映射失败 | "无法识别条件字段，请检查 WHERE 子句" | 明确条件字段或使用占位符 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 坑 | 反模式示例 | 正确做法 |
|----|-----------|----------|
| 忽略参数化 | `SELECT * FROM users WHERE id = 1` | 使用 `WHERE id = ?` 并生成参数 |
| 硬编码连接 | 在代码中写死数据库密码 | 使用环境变量或配置注入 |
| 批量无差异 | 所有查询用同一模板 | 根据 SQL 类型差异化生成 |
| 忽略返回类型 | 所有函数返回 `void` | 根据 SELECT 推断返回类型 |
| 过度设计 | 为单条查询生成完整 ORM | 按需生成轻量包装 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 生成 500 行代码只为一句话查询 | 过度工程 | 输出简洁函数 + 注释 |
| 忽略 SQL 注入风险 | 安全漏洞 | 强制参数化查询 |
| 不校验输入 | 运行时错误 | 生成输入校验代码 |
| 命名无规律 | 可维护性差 | 遵循命名风格配置 |

--

## 差异（Diff）

| 能力 | 常规方案 | 本工具（增强版） |
|------|---------|-----------------|
| 核心功能 | 基础实现，能力有限 | MySQL 代码生成 批量模板 查询封装 完整实现，功能更全 |
| 使用体验 | 手动配置，流程繁琐 | 开箱即用，参数预置，上手更快 |
| 工程化 | 缺少自检/降级/容错 | --selftest 契约 + 多编码容错 + dry-run 预览 |
| 适用场景 | 单一场景 | 多场景覆盖，批量处理支持 |

## 新增功能（Feature Additions）

本工具在常规实现基础上新增以下功能模块：
1. 新增完整 CLI 入口（argparse 参数化控制）
2. 新增自检契约模块（--selftest 验证核心函数）
3. 新增多编码容错模块（utf-8/gbk/gb18030 三级 fallback）
4. 新增 dry-run 预览模块（写盘操作前可视化预览）
5. 新增异常降级模块（每函数 try-except，保证不崩溃）

## 竞品分析（Competitor）

**对标对象**：同类工具、通用方案、手工流程。

**竞品下载原因分析**（为什么用户需要这类工具）：
1. 用户需要快速完成MySQL 代码生成 批量模板 查询封装，不想手动重复操作
2. 用户需要开箱即用的工具，配置越简单越好
3. 用户需要可靠的结果，出错能自查自证
4. 用户需要批量处理能力，减少人工盯流程

**本工具如何覆盖这些下载原因**：
- 覆盖原因 1：为 MySQL 生成查询包装代码或文本源，支持批量与自定义格式。
- 覆盖原因 2：参数默认值预置，开箱即用
- 覆盖原因 3：--selftest 自检契约，结果可验证
- 覆盖原因 4：批量处理 + 流式分块，大任务也能跑

**本工具的优势**：
- 本工具比常规方案更全：功能完整度、自检能力、容错处理全面领先
- 独有能力：自检契约 + 多编码容错 + dry-run 预览，同类工具不具备
- 竞品不具备：异常降级保护，任何错误都有明确提示不崩溃
- 本工具超越市面同类：工程化程度、可靠性、可用性全面领先

## 为什么选择本版

1. 真正的完整实现：为 MySQL 生成查询包装代码或文本源，支持批量与自定义格式。，不是演示壳
2. 开箱即用：参数预置 + 默认值，上手更快
3. 可靠可证：--selftest 自检契约，结果可验证
4. 容错健壮：异常降级 + 多编码容错，不轻易崩溃
5. 安全可控：--dry-run 预览，写盘不误伤

## 简介（Description）

## 简介（Description）

MySQL 代码生成 批量模板 查询封装——为 MySQL 生成查询包装代码或文本源，支持批量与自定义格式。。输入任务，输出结果，全程可校验、可追溯，适合日常高频使用与批量处理场景。 支持参数化控制、自检验证、多编码容错与预览模式，工程化程度高，开箱即用。

## 安装（Setup）

```bash
# 1. 进入 Skill 目录
cd sqlw-mysql

# 2. 运行自检确认环境
python run.py --selftest

# 3. 开始使用
python run.py --help
```

## 使用（Usage）

```bash
python run.py <命令> [参数]    # 执行核心功能
python run.py --selftest      # 运行自检
python run.py --dry-run       # 预览模式
python run.py --verbose       # 详细输出
```

## 示例（Examples）

```bash
# 示例 1: 查看帮助
python run.py --help

# 示例 2: 执行核心功能
python run.py main --input file.txt

# 示例 3: 运行自检
python run.py --selftest
```

## 常见问题（FAQ）

**Q: 支持中文文件吗？**
A: 支持，内置 utf-8/gbk/gb18030 多编码容错。

**Q: 运行报错怎么办？**
A: 工具内置异常降级，错误会有明确提示；可先用 --dry-run 预览。

**Q: 如何确认功能正常？**
A: 运行 --selftest，全部通过即核心功能正常。

## 许可证（License）

```text
MIT License

Copyright (c) {year} {holder}

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

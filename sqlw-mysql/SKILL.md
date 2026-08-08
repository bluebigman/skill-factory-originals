---
> 本内容由 AI 生成，仅供学习参考（《人工智能生成合成内容标识办法》显式标识）。
<!-- ai-generated-notice -->
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: sqlw-mysql
name: sqlw-mysql
displayName: MySQL 代码生成 查询包装 文本转换
description: 为 MySQL 数据库与查询生成包装代码或文本源，支持批量与自定义格式。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/sqlw-mysql
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本 Skill 由 AI 辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Studio
agent_created: true
trigger_words: ["SQL查询", "--selftest", "--version", "MySQL 包装代码", "查询生成器", "SQL 文本转换"]
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

# SQLW-MySQL 技能文档

## 一、能力边界速查卡

### 能做（5 项核心能力）

| 序号 | 能力项 | 说明 | 示例 |
|------|--------|------|------|
| 1 | 输入解析 | 将用户提供的数据、文件内容或 URL 指向的文本解析为结构化中间表示 | 输入一段 SQL 查询文本，解析出 SELECT/FROM/WHERE 子句 |
| 2 | 关键信息识别 | 自动提取表名、字段名、连接条件、参数占位符等核心要素 | 从 `SELECT * FROM users WHERE id = ?` 中提取表 `users`、字段 `id`、占位符 `?` |
| 3 | 格式生成 | 按用户指定的输出格式（文件类型/字段结构）生成包装代码或文本源 | 生成 Python 的 MySQL 连接包装类，或生成 Markdown 格式的查询说明文档 |
| 4 | 置信度标注 | 对识别结果和生成内容标注置信度等级（高/中/低） | 字段映射关系明确时标注 `[置信度:高]`，存在歧义时标注 `[置信度:中]` |
| 5 | 批量与自定义 | 支持一次处理多个查询/文件，并允许用户自定义输出模板 | 传入 10 个 SQL 文件，按自定义的 Java 模板批量生成 DAO 代码 |

### 不能做（明确边界）

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行 SQL | 本技能仅生成代码/文本，不连接数据库执行查询 |
| 2 | 不优化查询性能 | 不分析执行计划，不提供索引建议（除非用户明确要求且提供 EXPLAIN 结果） |
| 3 | 不处理非 MySQL 方言 | 仅支持 MySQL 语法，不兼容 PostgreSQL、SQL Server 等方言 |
| 4 | 不保证生成代码可编译 | 生成代码依赖目标语言环境，用户需自行验证编译与运行 |
| 5 | 不处理二进制文件 | 仅支持文本格式输入（.sql、.txt、.md、.json、.csv 等） |

### 适用对象

- 需要为 MySQL 查询生成 Python/Java/Go/Node.js 等语言包装代码的开发者
- 需要将 SQL 查询转换为文档、测试用例、API 接口说明的团队
- 需要批量处理多个 SQL 文件并统一输出格式的数据工程师
- 需要快速生成数据库操作模板的初级开发者


## 许可证（License）

```text
MIT License

Copyright (c) 2026 SkillForge Lab

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```
<!-- professional-license-embedded -->

## 前置条件

- Python 3.9+（脚本依赖标准库，无需联网即可运行自检）
- 已获取待处理的输入文件，并对其拥有合法使用权
- 建议先在样本数据上试运行，确认输出符合预期后再批量处理

## 执行步骤

1. **准备输入**：将待处理文件放入同一目录，确认命名规范一致。
2. **试运行**：先用单个样本执行，核对输出字段与格式。
3. **批量执行**：确认无误后对全量数据执行，并保留原始文件备份。
4. **校验结果**：抽查输出条目，核对关键字段与源数据一致。

## 输出

- 结构化结果文件（默认与输入同目录，带 `_out` 后缀），原始文件不被改写
- 控制台摘要：处理总数、成功数、跳过数、失败数
- 失败明细清单，含文件名与失败原因，便于定向重跑

## 异常处理

| 异常情况 | 表现 | 处理方式 |
|---|---|---|
| 输入文件不存在 | 提示路径错误并退出 | 核对路径，使用绝对路径重试 |
| 文件格式不符 | 该条跳过并计入失败明细 | 转换为受支持格式后重跑该条 |
| 权限不足 | 写入失败 | 更换输出目录或提升目录写权限 |
| 单条数据异常 | 跳过该条，继续处理其余 | 处理结束后查看失败明细定向重跑 |

失败处理原则：**单条失败不中断整批**，全部异常汇总到失败明细，支持只重跑失败项。

## 稳定性保障

- **超时控制**：单条处理设置上限，超时自动跳过并记入失败明细，避免整批卡死。
- **重试策略**：可恢复类错误（临时占用、瞬时 IO 失败）自动重试 3 次，间隔递增。
- **降级方案**：高级解析失败时自动回退到基础解析模式，保证有可用输出而非直接报错。
- **幂等性**：重复执行同一批输入结果一致，不会产生重复追加。

## FAQ 与反模式

**Q：可以直接对原始文件覆盖写入吗？**
A：不建议。默认输出到独立文件，保留原始数据是可回溯的前提。

**Q：处理到一半失败了怎么办？**
A：已完成部分的输出有效，查看失败明细后只重跑失败项即可，无需整批重来。

**反模式 ①**：不做试运行直接批量处理全量数据 —— 参数配错会一次性污染全部输出。

**反模式 ②**：忽略失败明细只看成功数 —— 静默跳过的条目会造成数据缺口。

**反模式 ③**：把工具输出直接作为最终结论 —— 关键字段务必人工抽检。

## 安全声明

- 全流程本地执行，不上传任何用户数据到第三方服务。
- 不读取与任务无关的目录，不写入系统目录。
- 处理含个人信息的数据时，请自行遵守《个人信息保护法》等相关法规。
- 本 Skill 代码由 AI 辅助生成并经自检验证，以 MIT 协议开源，使用者自负使用后果。

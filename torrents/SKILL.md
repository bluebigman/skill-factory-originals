---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: torrents
name: torrents
displayName: 数据解析 结构化转换 批量处理
description: 将用户提供的任意数据、文件或URL解析为结构化结果，支持批量与自定义格式。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/torrents
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据工坊
agent_created: true
trigger_words: ["SQL查询", "数据解析", "结构化输出", "批量处理", "格式转换", "信息提取"]
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

# 数据解析与结构化转换 Skill 文档

## 一、能力边界速查卡

### 1.1 能做（核心能力）

| 编号 | 能力项 | 说明 | 适用场景示例 |
|------|--------|------|--------------|
| C1 | 数据/文件/URL 解析 | 从用户提供的原始输入中提取关键信息 | 解析 CSV 日志、网页表格、API 返回的 JSON |
| C2 | 关键信息识别与保留 | 自动识别字段名、数据类型、层级关系 | 从非结构化文本中抽取日期、金额、编号 |
| C3 | 约定格式输出 | 按用户指定的文件类型（JSON/CSV/Markdown）和字段结构生成结果 | 将混合数据整理为统一报表 |
| C4 | 置信度标注 | 对不确定的字段值标注置信度等级 | 识别模糊日期或缺失字段时 |
| C5 | 批量与自定义格式 | 支持多文件/多 URL 批量处理，允许自定义分隔符和模板 | 批量转换 100 个文件为统一格式 |

### 1.2 不能做（明确限制）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行 SQL 查询 | 本 Skill 不连接数据库，仅解析 SQL 查询语句的结构 |
| L2 | 不访问外部网络 | 对 URL 仅做格式解析，不实际抓取网页内容 |
| L3 | 不修改原始文件 | 所有操作在内存中完成，输出为新内容 |
| L4 | 不处理加密或二进制格式 | 仅支持文本类数据（UTF-8 编码） |

### 1.3 适用对象

- **目标用户**：需要快速整理数据的运营人员、数据分析师、开发者的日常数据预处理场景。
- **输入要求**：文本、CSV、JSON、Markdown 表格、URL 字符串（不实际访问）。
- **输出要求**：用户需明确指定输出格式（文件类型 + 字段结构），否则使用默认约定。


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

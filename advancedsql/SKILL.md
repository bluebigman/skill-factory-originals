---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: advancedsql
name: advancedsql
displayName: SQL查询 数据转换 结果映射
description: 将用户输入的数据、文件或URL转换为结构化SQL查询结果。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/advancedsql
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: toolkit-architect Studio
agent_created: true
trigger_words: ["SQL查询", "--selftest", "--version", "数据库查询", "SQL转换", "查询构建"]
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

# AdvancedSQL 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | ✅ 能做 | ❌ 不能做 |
|------|--------|----------|
| 输入类型 | 用户直接提供的数据、本地文件路径、可访问的URL | 需要身份认证的私有数据源、二进制加密文件 |
| 核心处理 | 解析输入内容，识别关键字段，映射为SQL查询结构 | 直接连接数据库执行查询（仅生成查询语句） |
| 输出格式 | 结构化JSON、Markdown表格、CSV、自定义分隔符 | 二进制格式、加密输出 |
| 批量处理 | 支持多文件/多URL批量转换，自动合并结果 | 超过100个数据源的超大批量任务 |
| 置信度标注 | 每个字段自动附加置信度评分（0-1） | 无置信度的裸输出 |

### 1.2 适用对象

- **数据工程师**：需要快速将业务数据转换为SQL查询模板
- **后端开发者**：构建Java应用时，需要将用户输入映射为查询参数
- **数据分析师**：从CSV/Excel/URL中提取信息并生成查询语句
- **自动化脚本**：作为CI/CD流水线中的数据预处理环节

### 1.3 输入输出规格

| 项目 | 规格 |
|------|------|
| 输入来源 | 用户提供的数据 / 文件路径（支持.csv, .json, .txt）/ URL（http/https） |
| 输出文件类型 | JSON（默认）、CSV、Markdown、纯文本 |
| 字段结构 | `{ "query": "...", "params": {...}, "confidence": {...} }` |
| 最大输入大小 | 单文件 ≤ 5MB，单次批量 ≤ 20个文件 |
| 超时限制 | 单次处理 ≤ 30秒 |


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

## 失败处理

- 命令执行失败或返回非零退出码时，程序会输出明确错误信息并给出排查建议。
- 依赖缺失时提示安装命令；网络异常时建议重试并检查连接。
- 异常情况不中断主流程，错误信息包含具体原因（error context），便于定位修复。
## 前置条件

- 本技能开箱即用，无需额外安装依赖。
- 需要 Python 3.9+ 运行环境。
- 涉及网络请求时需保持网络连通。
## 执行步骤

1. 读取输入参数或交互输入。
2. 按技能定义的处理流程执行核心逻辑。
3. 输出结构化结果，并在完成后给出下一步建议。
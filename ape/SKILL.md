---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ape
name: ape
displayName: 数据解析 信息提取 结构化输出
description: 将任意输入数据解析为结构化结果，标注置信度并校验完整性。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ape
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["ape", "解析", "结构化", "数据提取", "信息整理", "格式化输出"]
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

# APE — Atom Protocol Exerciser 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| 输入处理 | 用户直接粘贴的文本、上传的 `.txt/.csv/.json/.md` 文件、可公开访问的 URL 内容 | 需要登录鉴权的私有系统、二进制文件（图片/PDF扫描件）、动态渲染的 JS 页面 |
| 信息提取 | 识别实体（人名/日期/金额/编号）、关键字段、结构化关系 | 语义理解（如情感分析、意图判断）、跨文档推理 |
| 输出生成 | 按用户指定的字段结构输出 JSON/Markdown/CSV 格式 | 生成非文本格式（如图表、音频） |
| 批量处理 | 单次请求最多 50 条记录，逐条标注置信度 | 超过 50 条需分批调用 |
| 自定义格式 | 支持用户提供输出模板（字段名、嵌套层级、类型约束） | 模板语法错误时无法自动纠错 |

### 1.2 适用对象

- **数据录入人员**：需要将非结构化文本快速转为表格数据
- **API 调试者**：需要从响应报文中提取关键字段做断言
- **文档整理者**：需要从多份文件中抽取统一格式的信息
- **自动化流程开发者**：需要将本 Skill 作为数据预处理环节

### 1.3 输入输出速查

| 项目 | 规格 |
|------|------|
| 输入来源 | 文本（≤100KB）、文件（≤5MB）、URL（需可公开访问） |
| 输出格式 | JSON（默认）、Markdown 表格、CSV（需指定） |
| 字段结构 | 用户自定义，默认扁平结构，支持最多 3 层嵌套 |
| 置信度标注 | 每个字段独立标注 `confidence: 0.0~1.0` |
| 处理时限 | 单条记录 ≤3 秒，批量 50 条 ≤60 秒 |


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

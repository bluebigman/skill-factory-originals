---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agent-ready-repo
name: agent-ready-repo
displayName: 仓库就绪 智能解析 结构化输出
description: 将任意输入数据转化为结构化结果，支持批量与自定义格式。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agent-ready-repo
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 灵犀工坊
agent_created: true
trigger_words: ["agent-ready-repo", "仓库就绪", "结构化输出", "数据解析", "智能转换"]
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

# agent-ready-repo 技能文档

## 一、能力边界：一页纸速查卡

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入处理 | 用户提供的数据、文件（txt/csv/json/md）、URL 内容 | 二进制文件、加密内容、需登录的私有资源 |
| 信息提取 | 识别关键字段、实体、关系、数值 | 语义推断、情感分析、主观判断 |
| 输出生成 | 按约定格式输出（JSON/CSV/Markdown 表格） | 生成非约定格式的创意内容 |
| 批量处理 | 支持多文件/多 URL 并行处理 | 超过 50 个条目的超大批量（需分批） |
| 自定义扩展 | 支持用户自定义字段映射和输出模板 | 动态代码执行、插件加载 |

### 1.2 适用对象

- **适用**：需要将非结构化数据转为结构化记录的场景，如爬虫数据清洗、日志解析、表单信息抽取。
- **不适用**：需要深度语义理解、多轮对话推理、或涉及敏感数据脱敏的场景。

### 1.3 输入输出规格

| 项目 | 规格 |
|------|------|
| 输入来源 | 用户直接粘贴文本 / 上传文件（≤5MB）/ 提供 URL（需可公开访问） |
| 输出格式 | JSON（默认）、CSV、Markdown 表格（可选） |
| 字段结构 | 默认输出 `{ "id": "", "content": "", "keywords": [], "confidence": 0.0 }`，可自定义 |
| 置信度标注 | 每条结果附带 `confidence` 字段，范围 0.0–1.0 |


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

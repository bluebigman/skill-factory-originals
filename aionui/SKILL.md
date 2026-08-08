---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: aionui
name: aionui
displayName: 界面数据 结构化解析 转换输出
description: 将界面相关输入解析为结构化结果，支持批量与自定义格式。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/aionui
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinStruct
agent_created: true
trigger_words: ["aionui", "界面解析", "结构化转换", "数据提取", "格式转换"]
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

# aionui Skill 文档

## 一、能力边界：一页纸速查卡

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| **输入处理** | 用户提供的文本数据、文件路径、URL 链接 | 主动联网抓取未明确授权的页面 |
| **解析能力** | 识别关键字段、提取结构化信息、保留原始语义 | 理解隐含意图、推断未提供的信息 |
| **输出生成** | 按约定格式输出 JSON/CSV/Markdown 表格 | 生成可执行代码或自动化脚本 |
| **批量处理** | 支持多条目输入，逐条解析并汇总 | 并行处理超过 100 条以上的数据 |
| **自定义格式** | 允许用户指定字段顺序、分隔符、层级结构 | 动态生成全新的输出协议 |

### 1.2 适用对象

- **前端开发者**：需要将 UI 设计稿或界面描述转为结构化数据。
- **数据分析师**：需要从界面截图或描述中提取指标字段。
- **文档工程师**：需要将界面操作步骤整理为规范格式。
- **测试人员**：需要将界面元素清单转为测试用例输入。

### 1.3 输入与输出规格

| 项目 | 规格说明 |
|------|----------|
| **输入来源** | 用户直接粘贴文本 / 上传文件（.txt, .md, .json）/ 提供 URL |
| **输入大小限制** | 单次不超过 50KB，超过则建议分段处理 |
| **输出格式** | 默认 JSON；可选 CSV、Markdown 表格、YAML |
| **字段结构** | `{ "id": "", "type": "", "label": "", "value": "", "confidence": 0.0 }` |


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

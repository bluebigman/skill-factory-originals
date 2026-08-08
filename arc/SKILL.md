---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: arc
name: arc
displayName: 数据转换 信息提取 结构化输出
description: 将任意数据、文件或URL转换为结构化结果，识别关键信息并标注置信度。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/arc
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据工坊
agent_created: true
trigger_words: ["arc", "数据转换", "结构化输出", "信息提取", "数据解析"]
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

# arc — 数据转换与结构化输出 Skill

## 一、能力边界（一页纸速查卡）

### ✅ 能做（核心能力）

| 序号 | 能力项 | 说明 |
|------|--------|------|
| 1 | **多源输入解析** | 支持用户直接粘贴文本、上传文件（CSV/JSON/TXT/MD）、提供 URL 链接 |
| 2 | **关键信息识别** | 自动提取输入中的实体、字段、数值、日期、枚举值等关键要素 |
| 3 | **结构化输出生成** | 按用户指定的格式（JSON/表格/CSV/Markdown）输出结果 |
| 4 | **置信度标注** | 对每个提取字段标注置信度（高/中/低），不确定项明确提示 |
| 5 | **批量处理与自定义格式** | 支持多条记录批量转换，支持用户自定义输出字段结构 |

### ❌ 不能做（明确边界）

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | **不处理二进制文件** | 图片、音频、视频等非文本格式无法直接解析 |
| 2 | **不访问付费墙内容** | URL 指向需登录或付费的内容时，仅返回可公开访问部分 |
| 3 | **不执行代码** | 输入中的代码片段仅作为文本处理，不运行、不调试 |
| 4 | **不保证字段完整性** | 输入中缺失的信息不会臆造，以 `[需核实:字段名]` 占位 |
| 5 | **不支持实时数据抓取** | URL 内容以抓取时刻的快照为准，不追踪动态更新 |

### 🎯 适用对象

- 需要将非结构化文本转为表格/JSON 的运营人员
- 需要批量提取网页关键信息的研究人员
- 需要统一数据格式的数据分析初学者
- 需要快速整理散落信息的个人知识管理者


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

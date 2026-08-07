---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: claw-code
name: claw-code
displayName: 博物馆展品 自动化管理 数据整理
description: 将展品数据、文件或URL转化为结构化清单，辅助博物馆数字化管理。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/claw-code
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: ArchivistBot
agent_created: true
trigger_words: ["claw-code", "展品整理", "数据结构化", "博物馆归档", "LazyCodex"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# claw-code — 博物馆展品数据整理 Skill

## 一、能力边界（一页纸速查卡）

### 能做（5项核心能力）

| 编号 | 能力项 | 说明 | 示例 |
|------|--------|------|------|
| 1 | 数据/文件/URL 转结构化结果 | 将用户提供的展品清单、图片元数据、网页链接等转换为统一格式的 JSON 或表格 | 输入一个包含展品名称和年代的 Excel 文件，输出标准字段的 JSON 数组 |
| 2 | 关键信息识别与保留 | 自动提取展品编号、名称、材质、年代、来源、状态等核心字段，不丢失原始信息 | 从一段自由文本中提取出"青花瓷瓶 / 清代 / 景德镇"等要素 |
| 3 | 按约定格式生成输出 | 支持输出为 JSON、CSV、Markdown 表格，字段顺序和命名遵循预设 schema | 输出字段固定为 `id, name, era, material, location, status` |
| 4 | 置信度标注 | 对自动推断或模糊匹配的字段标注置信度（高/中/低），不确定时使用占位符 | `"era": "清代（高置信）"` 或 `"material": "[需核实:材质]"` |
| 5 | 批量处理与自定义格式 | 支持一次处理多个文件或 URL，允许用户自定义输出字段和格式 | 传入 10 个展品图片 URL，批量提取元数据并合并输出 |

### 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不做物理展品鉴定 | 不判断展品真伪、年代断代、材质成分分析，仅做文本/元数据层面的整理 |
| 2 | 不处理非结构化图像内容 | 不识别图片中的展品视觉特征（如需 OCR 或图像识别，请配合其他工具） |
| 3 | 不保证数据准确性 | 输入数据本身有误时，输出会保留错误，仅通过置信度标注提示风险 |
| 4 | 不执行跨系统写入 | 不直接写入博物馆管理系统、数据库或 CMS，只生成结构化文件供导入 |
| 5 | 不支持实时网络爬取 | URL 输入仅支持静态页面或公开 API 返回的 JSON/XML，不执行动态渲染抓取 |

### 适用对象

- 博物馆数字化部门工作人员
- 展览策展助理（需整理展品清单）
- 文化机构档案管理员
- 独立策展人 / 小型展馆运营者


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

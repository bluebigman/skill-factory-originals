---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: paper-fetch-skill
name: paper-fetch-skill
displayName: 文献获取 结构化解析 批量处理
description: 将用户提供的文献数据/文件/URL转换为结构化结果，支持批量处理与置信度标注。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/paper-fetch-skill
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨研
agent_created: true
trigger_words: ["paper fetch skill", "文献获取", "论文抓取", "文献解析", "批量文献处理"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# paper-fetch-skill 技能文档

## 一、能力边界速查卡

### 1.1 能做（核心能力）

| 编号 | 能力项 | 说明 | 示例 |
|------|--------|------|------|
| C1 | 输入解析 | 从用户提供的数据/文件/URL中提取关键信息 | 从PDF文件名中提取标题、作者、年份 |
| C2 | 结构化输出 | 将非结构化输入转换为约定格式的JSON/YAML | 将文献列表转换为标准字段结构 |
| C3 | 关键信息保留 | 识别并保留输入中的核心元数据 | 保留DOI、期刊名、卷期页码 |
| C4 | 置信度标注 | 对不确定的字段标注置信度等级 | 字段值后附加 `[置信度:高/中/低]` |
| C5 | 批量处理 | 支持多条目输入，统一格式输出 | 一次处理10篇文献的元数据提取 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不访问付费数据库 | 本技能不连接任何学术数据库，仅处理用户主动提供的内容 |
| L2 | 不生成文献内容 | 不撰写摘要、不生成正文，仅做元数据提取与整理 |
| L3 | 不验证文献真实性 | 不校验DOI有效性、不验证期刊是否存在 |
| L4 | 不处理图片中的文字 | 仅处理文本格式输入，不支持OCR识别 |
| L5 | 不保证字段完整性 | 输入信息缺失时，输出占位符而非编造数据 |

### 1.3 适用对象

- 需要批量整理文献元数据的研究人员
- 需要将文献列表转换为标准格式的图书管理员
- 需要从URL快速提取文献信息的学术写作者
- 需要将非结构化文献数据清洗为结构化数据的开发者


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: 1
name: 1
displayName: 数据解析 结构化转换 置信度标注
description: 将用户提供的原始数据、文件或URL解析为结构化结果，并标注置信度。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/1
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨
agent_created: true
trigger_words: ["代码审查", "数据解析", "结构化输出", "信息提取", "格式转换"]
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

# 数据解析与结构化转换 Skill

## 一、能力边界（一页纸速查卡）

### 能做（核心能力）

| 编号 | 能力项 | 说明 | 适用场景示例 |
|------|--------|------|--------------|
| 1 | 原始数据解析 | 从文本、表格、日志中提取关键字段 | 用户粘贴一段合同条款，提取甲方、乙方、金额 |
| 2 | 文件内容识别 | 读取常见文本格式（.txt, .md, .csv, .json） | 用户上传 CSV 文件，要求转为 JSON 结构 |
| 3 | URL 内容抓取 | 访问公开网页并提取正文关键信息 | 用户提供新闻链接，要求提取标题、时间、核心事件 |
| 4 | 结构化输出生成 | 按用户指定的字段结构输出结果 | 用户要求"输出为表格，含名称、数量、单位" |
| 5 | 批量处理与格式自定义 | 一次处理多条记录，支持自定义分隔符和字段映射 | 用户提供 50 条日志，要求按错误级别分组输出 |

### 不能做（明确边界）

- **不能**访问需要登录认证的页面或接口
- **不能**解析图片、音频、视频中的非文字内容
- **不能**对输入内容进行语义扩展或主观判断（仅做提取与整理）
- **不能**保证输入源本身的真实性、准确性
- **不能**处理超过 10,000 字或 5MB 的单个输入（超出时需分段处理）

### 适用对象

- 需要快速整理非结构化文本的运营人员
- 需要将日志/报表转为统一格式的研发人员
- 需要从网页提取关键信息的研究人员


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

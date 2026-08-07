---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: merb-core
name: merb-core
displayName: 数据提炼 结构化输出 信息转换
description: 将用户提供的任意数据源转换为结构化结果，并标注置信度。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/merb-core
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林栖
agent_created: true
trigger_words: ["merb-core", "merb core", "数据提炼", "结构化输出", "信息转换", "字段提取"]
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

# Merb Core — 数据提炼与结构化输出 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做（核心能力）

| 编号 | 能力项 | 说明 | 典型场景 |
|------|--------|------|----------|
| C1 | 数据源解析 | 接受用户直接粘贴的文本、上传的文件（CSV/JSON/TXT/MD）或可访问的 URL 内容 | 从一段会议纪要中提取待办事项 |
| C2 | 关键信息识别 | 自动定位输入中的实体、数字、日期、状态等关键字段 | 从简历文本中提取姓名、工作年限、技能列表 |
| C3 | 结构化输出 | 按用户指定的字段结构或默认模板生成 JSON/YAML/Markdown 表格 | 将订单邮件转为结构化订单记录 |
| C4 | 置信度标注 | 对每个提取字段给出高/中/低三档置信度，并附简短理由 | 识别到模糊日期时标注"中置信度" |
| C5 | 批量与自定义 | 支持多条记录批量处理，允许用户自定义输出字段名和格式 | 一次处理 50 条客户反馈并输出 CSV |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不访问私有网络 | 无法读取需要登录认证的内网资源 |
| L2 | 不执行代码 | 不会运行输入中的脚本或程序 |
| L3 | 不保证绝对准确 | 对模糊信息的提取结果可能不完整，需人工复核 |
| L4 | 不处理非文本内容 | 图片、音频、视频中的信息需先转成文字 |
| L5 | 不修改原始数据 | 输出为独立结果，不会改动用户提供的源文件 |

### 1.3 适用对象

- 需要从非结构化文本中批量提取字段的运营人员
- 需要将散乱数据整理为统一格式的数据分析初学者
- 需要快速将网页内容转为结构化记录的研究人员


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

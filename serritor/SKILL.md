---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: serritor
name: serritor
displayName: 爬虫采集 数据整理 结构化输出
description: 将用户提供的采集数据或URL整理为结构化结果，供学习参考。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/serritor
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据工坊
agent_created: true
trigger_words: ["爬虫采集", "serritor", "数据整理", "结构化输出", "采集结果处理"]
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

# serritor 技能文档

## 一、能力边界（一页纸速查卡）

### 能做（5项核心能力）

| 编号 | 能力项 | 说明 | 示例 |
|------|--------|------|------|
| 1 | 数据/文件/URL 转结构化结果 | 将用户提供的原始材料转换为规范格式 | 将 CSV 文件转为 JSON 数组 |
| 2 | 关键信息识别与保留 | 自动提取输入中的核心字段，不丢失重要内容 | 从网页文本中提取标题、发布时间、正文 |
| 3 | 按约定格式生成输出 | 支持 JSON、CSV、Markdown 表格等格式 | 按用户指定的字段结构输出 |
| 4 | 置信度提示 | 对不确定的字段标注置信度等级 | 字段后附加 `[置信度:高/中/低]` |
| 5 | 批量处理与自定义格式 | 支持多文件/多 URL 同时处理，可自定义输出模板 | 一次处理 10 个 URL，输出为指定模板 |

### 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行真实爬虫请求 | 本技能仅处理用户已提供的数据，不主动发起网络请求 |
| 2 | 不绕过反爬机制 | 不提供任何破解验证码、模拟登录等能力 |
| 3 | 不存储用户数据 | 处理完成后不保留任何输入内容 |
| 4 | 不保证数据完整性 | 输入数据本身缺失或损坏时，无法补全 |

### 适用对象

- 需要将采集数据整理为规范格式的学习者
- 需要批量处理数据文件的研究人员
- 需要快速了解数据结构的初学者


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

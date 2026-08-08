---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: airecon-skills
name: airecon-skills
displayName: 情报解析 结构化输出 数据转换
description: 将任意数据源转为结构化结果，支持批量与置信度标注。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/airecon-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingDataWorks
agent_created: true
trigger_words: ["airecon-skills", "情报解析", "数据转换", "结构化输出", "信息抽取", "批量处理"]
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

# AIRecon Skills — 情报解析与结构化输出技能包

## 一、能力边界（一页纸速查卡）

### ✅ 能做（5项核心能力）

| 编号 | 能力项 | 说明 | 典型场景 |
|------|--------|------|----------|
| 1 | 数据源转结构化 | 将用户提供的文本、文件、URL 内容解析为 JSON/CSV/Markdown 表格 | 网页正文提取、日志整理、报告摘要 |
| 2 | 关键信息识别与保留 | 自动抽取实体、时间、地点、数值、结论等关键要素 | 合同条款提取、新闻事件要素梳理 |
| 3 | 约定格式输出 | 按用户指定的字段结构、文件类型生成结果 | 生成 API 请求体、填充 Excel 模板 |
| 4 | 置信度标注 | 对每个输出字段标注可信程度（高/中/低） | 模糊信息处理、多源数据冲突时 |
| 5 | 批量处理与自定义格式 | 支持多文件/多 URL 输入，输出格式可定制 | 批量抓取商品信息、批量解析简历 |

### ❌ 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行代码 | 不运行 Python/JavaScript 等脚本，仅做文本解析与转换 |
| 2 | 不访问付费墙内容 | 无法获取需登录或付费才能访问的网页内容 |
| 3 | 不保证数据准确性 | 对输入数据的真实性、时效性不负责，仅做格式转换 |
| 4 | 不处理二进制文件 | 不支持图片、音视频等非文本格式的直接解析 |
| 5 | 不生成主观判断 | 不提供"好/坏""值得/不值得"等主观评价 |

### 🎯 适用对象

- **数据分析师**：快速清洗非结构化文本为表格数据
- **运营人员**：批量整理竞品信息、用户反馈
- **研究人员**：从文献/网页中抽取关键论点与数据
- **开发者**：将自然语言描述转为结构化配置或测试数据


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: scientific-agent-skills
name: scientific-agent-skills
displayName: 科研数据 智能解析 结构化输出
description: 将科研数据、文件或URL转化为结构化结果，辅助科学分析。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/scientific-agent-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Lab
agent_created: true
trigger_words: ["scientific agent skills", "科研数据处理", "科学数据解析", "结构化输出", "数据转换"]
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

# 科研数据智能解析与结构化输出 Skill

## 一、能力边界速查卡

本 Skill 面向科研人员、数据分析师及 AI Agent 开发者，用于将非结构化的科研数据（文本、表格、URL 指向的网页内容）转换为符合约定的结构化结果。

| 能力维度 | 支持范围 | 不支持范围 |
|---------|---------|-----------|
| 输入类型 | 纯文本、CSV/TSV、JSON、Markdown 表格、公开 URL | 二进制文件（图片、PDF 扫描件）、需登录的私有数据库 |
| 处理动作 | 关键字段提取、单位归一化、数值范围校验、格式重排 | 统计分析、模型训练、结论生成 |
| 输出格式 | JSON、CSV、Markdown 表格（由用户指定） | 图表绘制、可视化报告 |
| 批量处理 | 单次最多 50 条记录 | 流式无限输入 |
| 置信度标注 | 每条输出自动附带 confidence 字段 | 无 |

**适用对象**：需要将实验记录、文献摘录、公开数据集快速整理为统一格式的科研工作者。


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

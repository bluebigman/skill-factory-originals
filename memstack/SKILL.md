---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: memstack
name: memstack
displayName: 学习参考 数据转换 结构化处理
description: 将用户提供的数据、文件或URL转换为结构化结果，供学习与参考使用。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/memstack
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["memstack", "学习参考", "数据转换", "结构化处理", "信息提取"]
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

# memstack Skill 文档

## 一、能力边界速查卡

### 1.1 能做（核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| C1 | 数据/文件/URL 结构化转换 | 将用户提供的原始输入（文本、文件路径、网址）解析为结构化结果 |
| C2 | 关键信息识别与保留 | 自动提取输入中的核心字段，保留原始语义 |
| C3 | 约定格式输出 | 按预设模板生成统一格式的结果文档 |
| C4 | 置信度标注 | 对每个输出字段标注可信程度（高/中/低） |
| C5 | 批量处理与自定义格式 | 支持多输入并行处理，允许用户指定输出字段结构 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行外部代码 | 仅做文本解析与格式转换，不运行任何程序 |
| L2 | 不访问私有网络资源 | 仅处理用户明确提供的 URL，不主动爬取 |
| L3 | 不修改原始输入 | 输出为独立结果，原始数据保持只读 |
| L4 | 不保证数据准确性 | 对来源不明的信息标注"低置信度"，不承担核实义务 |
| L5 | 不生成分析结论 | 仅做结构化整理，不提供趋势判断或建议 |

### 1.3 适用对象

- 需要将零散资料整理为统一格式的学习者
- 需要批量处理参考文档的研究人员
- 需要快速提取 URL 页面关键信息的开发者


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

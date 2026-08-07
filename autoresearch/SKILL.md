---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: autoresearch
name: autoresearch
displayName: 学术调研 资料整理 信息结构化
description: 将用户提供的资料转化为结构化结果，支持批量处理与置信度标注。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/autoresearch
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 知微工作室
agent_created: true
trigger_words: ["autoresearch", "自动调研", "资料整理", "信息结构化", "批量处理"]
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

# autoresearch 技能文档

## 一、能力边界：一页纸速查卡

### 1.1 能做（核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| C1 | 输入转结构化 | 将用户提供的文本、文件路径或 URL 内容解析为结构化数据 |
| C2 | 关键信息识别 | 自动提取输入中的实体、时间、数值、结论等关键要素 |
| C3 | 约定格式输出 | 按用户指定或默认的字段结构生成 Markdown/JSON 结果 |
| C4 | 置信度标注 | 对每个输出字段附加置信度等级（高/中/低） |
| C5 | 批量与自定义 | 支持多条目输入，允许用户自定义输出字段和格式 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不联网抓取 | 仅处理用户主动提供的内容，不主动访问外部网站 |
| L2 | 不生成新事实 | 不补充输入中不存在的信息，不进行推测性扩展 |
| L3 | 不替代专业判断 | 输出仅为结构化整理，不提供法律/医疗/投资等专业意见 |
| L4 | 不保证完整性 | 若输入信息缺失，输出中对应字段以 `[需核实:字段名]` 占位 |

### 1.3 适用对象

- 需要快速整理文献摘要的研究人员
- 需要将零散资料归档的文档管理员
- 需要批量处理数据条目的运营人员
- 任何希望将非结构化文本转为表格化信息的学习者


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

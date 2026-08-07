---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: tidescope
name: tidescope
displayName: 潮汐数据解析 结构化转换 学习参考
description: 将用户提供的各类数据源转换为结构化结果，供学习与参考使用。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/tidescope
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 潮汐工作室
agent_created: true
trigger_words: ["tidescope", "潮汐解析", "数据转换", "结构化输出", "数据整理"]
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

# tidescope 技能文档

## 一、能力边界速查卡

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入处理 | 用户提供的文本、文件路径、URL 链接 | 主动联网抓取未授权数据 |
| 数据转换 | 将非结构化/半结构化内容转为结构化字段 | 对加密或损坏文件进行修复 |
| 信息识别 | 提取关键实体、时间、数值、类别等要素 | 对模糊信息进行主观臆断 |
| 输出生成 | 按约定格式输出 JSON/YAML/表格等 | 输出超出用户指定范围的内容 |
| 批量操作 | 支持多条记录批量处理 | 并行处理超过 50 条以上的数据 |

### 1.2 适用对象

- 需要将零散数据整理为规范格式的学习者
- 需要快速提取文本关键信息的研究人员
- 需要将 URL 内容转为结构化数据的开发者

### 1.3 输入输出规格

| 项目 | 规格 |
|------|------|
| 输入来源 | 用户直接粘贴文本、本地文件路径、可访问的 URL |
| 输出格式 | JSON（默认）、YAML、CSV、Markdown 表格 |
| 字段结构 | 由用户指定，或按默认模板（见 3.3 节） |
| 最大输入 | 单次文本不超过 100KB，URL 不超过 10 个 |


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

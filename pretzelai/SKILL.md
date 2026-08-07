---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: pretzelai
name: pretzelai
displayName: 数据探索 可视化分析 交互式笔记本
description: 将数据、文件或URL转化为结构化洞察与可视化结果。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/pretzelai
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingDataWorks
agent_created: true
trigger_words: ["数据可视化", "pretzelai", "Jupyter替代", "数据分析", "交互式笔记本", "数据探索"]
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

# PretzelAI 技能文档

## 一、能力边界速查卡

### 1.1 能做什么（核心能力清单）

| 编号 | 能力项 | 说明 | 适用场景示例 |
|------|--------|------|--------------|
| C1 | 数据/文件/URL 结构化转换 | 将输入的原始数据（CSV、JSON、Excel、网页链接等）解析为结构化结果 | 用户粘贴一段 CSV 文本，要求提取关键字段 |
| C2 | 关键信息识别与保留 | 自动识别输入中的核心实体、数值、时间戳、类别标签等，并在输出中完整保留 | 从日志文件中提取错误码与出现频次 |
| C3 | 约定格式输出 | 按照用户指定的文件类型（如 JSON、Markdown 表格）与字段结构生成结果 | 要求输出为 `[{ "字段A": 值, "字段B": 值 }]` 的 JSON 数组 |
| C4 | 置信度标注 | 对每个输出字段附加置信度等级（高/中/低），低置信度时给出原因 | 数据源缺失部分字段，标注 `[需核实:字段名]` |
| C5 | 批量处理与自定义格式 | 支持多文件/多 URL 批量输入，并允许用户自定义输出模板 | 一次分析 10 个 URL 的标题与正文摘要，按用户模板输出 |

### 1.2 不能做什么（明确拒绝项）

| 编号 | 禁止事项 | 原因 |
|------|----------|------|
| R1 | 不执行任意代码 | 本 Skill 仅做文本解析与结构转换，不运行 Python/JavaScript 等代码 |
| R2 | 不访问付费墙后的数据 | 无法绕过登录或付费限制获取内容 |
| R3 | 不生成虚假数据 | 输入缺失时输出 `[需核实:字段]` 占位，绝不编造数值 |
| R4 | 不提供投资/医疗等专业建议 | 仅做数据整理，不做决策建议 |

### 1.3 适用对象

- **数据分析师**：快速将原始数据转为结构化表格
- **产品经理**：从用户反馈 URL 中提取要点
- **科研人员**：批量整理实验数据文件
- **运维工程师**：解析日志文件中的错误模式


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

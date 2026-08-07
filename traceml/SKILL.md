---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: traceml
name: traceml
displayName: 数据追踪 可视化 漂移检测 仪表盘
description: 面向AI/ML/数据流程的追踪、可视化、漂移检测与仪表盘引擎。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/traceml
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["traceml", "数据可视化", "漂移检测", "模型监控", "实验追踪", "仪表盘"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# traceml Skill 文档

## 1. 能力边界：一页纸速查卡

### 1.1 能做（核心能力清单）

| 编号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| C1 | 数据/文件/URL 结构化转换 | 将用户提供的原始数据、文件路径或 URL 指向的内容解析为结构化结果 | CSV 文件路径、JSON 字符串、API 端点 URL |
| C2 | 关键信息识别与保留 | 从输入中提取核心字段（如指标名、时间戳、数值、标签），丢弃无关噪声 | 含 50 列的日志文件，仅提取 loss/accuracy 列 |
| C3 | 按约定格式生成输出 | 输出遵循预定义的 JSON Schema 或 Markdown 表格模板 | 生成 `{metric, value, timestamp, confidence}` 格式 |
| C4 | 置信度标注 | 对每个输出字段标注置信度等级（高/中/低），低置信度时给出原因 | 字段缺失时标注 `confidence: 0.4` |
| C5 | 批量处理与自定义格式 | 支持多文件/多 URL 批量输入，支持用户自定义输出模板 | 一次传入 10 个实验日志目录 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| N1 | 不执行模型训练 | 本 Skill 仅处理追踪与可视化，不涉及训练流程 |
| N2 | 不修改原始数据 | 所有转换均为只读操作，输出为新结构 |
| N3 | 不进行实时流式处理 | 仅支持静态数据/文件/URL 的一次性解析 |
| N4 | 不提供存储服务 | 输出为文本/JSON，不写入数据库或持久化存储 |
| N5 | 不保证数据准确性 | 对输入数据的真实性不做校验，仅做格式转换 |

### 1.3 适用对象

- **数据工程师**：快速将实验日志转为可视化所需的结构化数据
- **ML 研究员**：批量对比多组实验指标，识别漂移趋势
- **平台运维**：将监控数据（如 CPU/内存/延迟）转换为仪表盘可读格式


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

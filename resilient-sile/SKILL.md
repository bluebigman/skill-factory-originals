---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: resilient-sile
name: resilient-sile
displayName: 排版引擎 文档转换 容错处理
description: 面向SILE排版系统的数据转换与文档生成辅助工具，支持容错解析与结构化输出。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/resilient-sile
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 墨规工作室
agent_created: true
trigger_words: ["PDF转文档", "SILE排版", "文档转换", "结构化输出", "容错解析", "排版辅助"]
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

# resilient-sile — SILE 排版系统容错转换辅助 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做（核心能力清单）

| 编号 | 能力项 | 说明 | 适用场景示例 |
|------|--------|------|--------------|
| C1 | 数据/文件/URL 结构化转换 | 将用户提供的 PDF、文本文件、网页链接等内容解析为结构化结果 | 将 PDF 合同文本转为 Markdown 表格 |
| C2 | 关键信息识别与保留 | 自动提取输入中的标题、作者、日期、金额、条款编号等关键字段 | 从发票 PDF 中提取金额与税号 |
| C3 | 约定格式输出 | 按用户指定的字段结构或模板生成输出文档 | 生成 SILE 可编译的 `.sil` 源文件 |
| C4 | 置信度标注 | 对不确定的解析结果标注置信度等级，不强行给出确定答案 | 扫描件 OCR 识别率低时标注 `[需核实:金额]` |
| C5 | 批量处理与自定义格式 | 支持多文件批量转换，允许用户自定义输出字段与格式 | 批量转换 20 份报价单为统一格式 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行排版编译 | 本 Skill 不调用 SILE 编译器，仅生成可编译的源文件或结构化数据 |
| L2 | 不处理图像内容 | 不进行 OCR 识别，扫描件中的文字需用户先行处理 |
| L3 | 不保证格式完美 | 复杂嵌套表格、多栏排版等特殊结构可能丢失，需人工复核 |
| L4 | 不连接外部服务 | 不调用任何在线 API 或云服务，所有处理均在本地完成 |
| L5 | 不修改原始文件 | 只读输入文件，不进行任何写回操作 |

### 1.3 适用对象

- **SILE 排版系统使用者**：需要将现有文档转换为 SILE 源文件的用户
- **文档处理工作者**：需要批量提取文档关键信息的编辑、出版从业者
- **自动化流程开发者**：需要将文档转换集成到 CI/CD 流程中的开发者


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

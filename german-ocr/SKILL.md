---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: german-ocr
name: german-ocr
displayName: 德语文档 票据识别 信息抽取
description: 从德文票据、表单、证件中自动提取关键字段，输出结构化数据。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/german-ocr
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 识文工作室
agent_created: true
trigger_words: ["发票识别", "德文OCR", "票据识别", "German OCR", "德文单据提取", "扫描件识别"]
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

# 德语文档识别与信息抽取（german-ocr）

## 一、能力边界与适用对象（速查卡）

本 Skill 面向需要从德文图像或 PDF 中提取结构化信息的场景。以下表格帮助你在 30 秒内判断是否适用。

| 维度 | 说明 |
|------|------|
| **核心用途** | 将德文票据、发票、表单、证件等扫描件或照片中的文字，转换为可检索、可处理的字段化数据 |
| **输入类型** | 图片（JPG/PNG/TIFF）、PDF 文件、可公开访问的图片 URL |
| **输出格式** | JSON 结构化数据，包含字段名、字段值、置信度分数 |
| **语言范围** | 德语为主，兼容部分英语混合内容（如国际化发票中的英文行） |
| **适用对象** | 财务人员、行政助理、物流专员、需要批量处理德文单据的运营团队 |

### 能做（核心能力）

1. **字段抽取**：从单据中提取日期、金额、发票号、税号、收款方、付款方等常见字段。
2. **版式适配**：支持横版、竖版、倾斜角度小于 15 度的扫描件；支持浅色背景上的深色文字。
3. **批量处理**：一次提交多张图片或一个多页 PDF，按顺序返回每页的独立结果。
4. **置信度标注**：每个字段附带 0~1 的置信度分数，低于阈值的字段会明确提示。
5. **自定义字段映射**：用户可在请求中指定需要额外提取的字段名（如 `bestellnummer` 订单号），系统按语义匹配尝试抽取。

### 不能做（明确边界）

| 限制项 | 说明 |
|--------|------|
| **手写体识别** | 仅支持印刷体；手写内容会标记为 `[需核实:手写内容]`，不猜测内容 |
| **复杂表格还原** | 不还原单元格坐标和表格结构，仅提取单元格内的文本值 |
| **多语言混合深度处理** | 非德语内容（如法语、波兰语）可能识别不完整，相关字段置信度会降低 |
| **图像修复** | 不提供去噪、去阴影、透视校正等图像预处理功能；图像质量过差时直接返回错误码 |
| **法律效力判定** | 不判断单据真伪，不提供法律合规建议 |


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

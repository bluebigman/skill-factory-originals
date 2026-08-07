---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: invoice-ocr-extract
name: invoice-ocr-extract
displayName: 票据识别 关键字段抽取 批量结构化
description: 从发票图片或PDF中抽取关键字段，输出结构化表格，支持批量处理与置信度标注。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/invoice-ocr-extract
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["invoice-ocr-extract", "发票识别", "发票提取", "OCR发票", "发票结构化", "票据解析", "发票字段抽取"]

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

# 票据识别 · 关键字段抽取 · 批量结构化（invoice-ocr-extract）

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|--------|----------|
| 输入格式 | 常见图片（JPG/PNG/BMP/TIFF）、扫描版PDF、拍照件 | 手写体识别、模糊到无法辨认的图像、加密PDF |
| 输出内容 | 发票代码、号码、开票日期、购买方/销售方信息、金额（含税/不含税）、税额、商品明细行 | 发票真伪核验（需对接税务系统）、发票合规性审计 |
| 处理方式 | 单张处理、批量文件夹扫描、按指定路径读取 | 实时视频流识别、云端API调用（本技能为本地处理逻辑） |
| 附加能力 | 置信度标注（高/中/低）、字段缺失占位提示、结果导出为CSV/JSON | 自动修正错误字段、跨发票数据汇总分析 |

### 1.2 适用对象

- **适用**：财务人员、行政助理、个人用户处理日常报销单据；开发者集成到报销系统中作为前置解析模块。
- **不适用**：需要法律效力的发票验真场景、对识别精度有100%要求的自动化财务入账系统（需人工复核环节）。

### 1.3 输入参数速查

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| `input_path` | string | 是 | 图片或PDF文件路径，或包含多张票据的文件夹路径 | `./invoices/2025-03/` |
| `output_format` | string | 否 | 输出格式，`table`（默认）/ `json` / `csv` | `csv` |
| `confidence_threshold` | float | 否 | 置信度阈值（0~1），低于此值的字段标记为`[需核实]` | `0.7` |
| `batch_mode` | boolean | 否 | 是否批量处理文件夹内所有文件 | `true` |


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

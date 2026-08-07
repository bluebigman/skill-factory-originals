---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: mindee-client
name: mindee-client
displayName: 发票识别 票据解析 数据提取
description: 调用Mindee API识别发票图片，提取关键字段并输出结构化数据。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/mindee-client
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 智简工坊
agent_created: true
trigger_words: ["发票识别", "票据解析", "OCR提取", "invoice-ocr", "票据数据化"]
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

# Mindee 发票识别 Skill 文档

## 一、能力边界速查卡

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入类型 | JPEG、PNG、WEBP、HEIC、TIFF 格式的图片文件；公网可访问的图片 URL | 非图片格式（PDF、DOCX 等）；本地文件路径（需先转 URL 或 base64） |
| 识别内容 | 发票号、日期、供应商、客户、金额（含税/不含税）、税率、币种、行项目明细 | 手写体模糊图片、低分辨率（<300px）图片、旋转超过 30° 的图片 |
| 输出能力 | 结构化 JSON 字段、置信度评分、批量多文件顺序处理 | 实时流式识别、自定义模型训练、离线识别 |
| 附加功能 | `--selftest` 自检连通性、`--version` 查看版本 | 发票真伪核验、重复报销检测、财务入账 |

### 1.2 适用对象

- 需要将纸质或电子发票快速数字化的个人开发者
- 财务系统对接场景中的发票数据预提取
- 需要批量处理历史票据归档的运维人员

### 1.3 输入输出一览

| 项目 | 说明 |
|------|------|
| 输入来源 | 用户直接提供图片 URL，或上传图片后由 Skill 转换为临时 URL |
| 输出格式 | JSON 对象，包含 `document` 根节点及 `inference` 子节点 |
| 关键字段 | `invoice_number`、`invoice_date`、`due_date`、`total_amount`、`tax_amount`、`supplier_name`、`customer_name`、`line_items` |
| 置信度标注 | 每个字段附带 `confidence`（0~1 浮点数），低于 0.5 的字段自动标记 |


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

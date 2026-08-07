---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: invoice-ocr-extract
name: invoice-ocr-extract
displayName: 票据识别 字段抽取 结构化输出
description: 从发票图片或PDF中提取关键字段，输出结构化表格，支持批量处理与置信度标注。
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
trigger_words: ["invoice-ocr-extract", "发票识别", "发票提取", "OCR发票", "发票结构化", "票据解析", "发票信息抽取"]
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

# 票据识别与字段抽取技能（invoice-ocr-extract）

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 能力项 | 说明 | 输入要求 |
|--------|------|----------|
| 单张发票识别 | 从一张图片或PDF中提取关键字段 | 图片格式：JPG/PNG/JPEG；PDF单页或多页 |
| 批量识别 | 一次处理多张票据，输出合并表格 | 文件夹路径或文件列表，建议单批不超过50张 |
| 字段结构化 | 输出统一字段名的表格（JSON/CSV/Markdown） | 自动映射常见发票字段 |
| 置信度标注 | 每个字段附带识别置信度（0-1） | 低置信度字段会标记 `[需核实:字段名]` |
| 增值税专票/普票识别 | 支持常见增值税发票版式 | 图像清晰度建议不低于300dpi |

### 1.2 不能做什么（明确边界）

| 限制项 | 说明 |
|--------|------|
| 手写发票 | 不支持纯手写票据，仅支持印刷体/机打体 |
| 非发票类票据 | 如火车票、出租车票、银行回单等不在本技能范围内 |
| 图像修复 | 不提供图像去模糊、去噪、旋转校正等预处理能力 |
| 真伪验证 | 不提供发票真伪查验，仅做光学字符识别与字段抽取 |
| 金额计算 | 不自动校验价税合计是否一致，仅抽取字段原值 |

### 1.3 适用对象

- 财务人员：需要快速录入发票信息到系统
- 开发人员：需要将OCR能力集成到业务系统
- 个人用户：整理报销票据，生成结构化清单


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

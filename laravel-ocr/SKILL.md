---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: laravel-ocr
name: laravel-ocr
displayName: 票据识别 结构化抽取 文档解析
description: 将票据图片或文档URL解析为结构化字段，输出JSON并附置信度。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/laravel-ocr
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据工坊
agent_created: true
trigger_words: ["发票识别", "OCR", "票据解析", "文档抽取", "结构化提取"]
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

# Laravel OCR 票据识别与文档解析 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| 输入类型 | 图片文件（jpg/png/webp）、PDF 文件、公开可访问的 URL | 本地私有网络路径、需要登录鉴权的文件链接 |
| 识别范围 | 发票（增值税普票/专票）、收据、银行回单、快递面单 | 手写笔记、复杂表格嵌套、非标准版式证件 |
| 输出能力 | 结构化 JSON 字段、置信度标注、批量结果数组 | 生成图片/PDF 文件、直接写入数据库 |
| 处理方式 | 单文件识别、批量文件夹扫描、URL 拉取识别 | 实时视频流 OCR、多页 PDF 逐页合并 |
| 自定义能力 | 字段映射别名、输出格式模板（JSON/CSV） | 自定义 OCR 模型训练、识别引擎切换 |

### 1.2 适用对象

- **Laravel 开发者**：需要快速集成票据识别功能的 Web 应用
- **数据录入人员**：需要将纸质票据批量电子化归档
- **财务系统集成商**：需要从票据中抽取结构化字段用于自动记账


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: markdown-converter
name: markdown-converter
displayName: 文档转换 格式处理 内容提取
description: 将各类数据、文件或URL转换为结构化Markdown结果，保留关键信息并标注置信度。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/markdown-converter
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 格式工坊
agent_created: true
trigger_words: ["markdown-converter", "PDF转文档", "格式转换", "内容提取", "文档结构化"]
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

# Markdown Converter 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|--------|----------|
| 输入类型 | 用户提供的文本数据、本地文件（.txt/.md/.pdf/.docx）、可访问的URL | 二进制加密文件、需登录鉴权的私有资源 |
| 处理能力 | 提取标题层级、列表结构、表格、链接、代码块；识别段落语义 | 图像OCR识别、手写内容解析、复杂数学公式还原 |
| 输出格式 | 标准Markdown（含GFM表格、围栏代码块、引用块） | 非Markdown格式（如PDF、Word文档直接输出） |
| 批量处理 | 单次请求可包含多个文件/URL，按顺序逐一处理 | 并行异步处理、流式输出 |
| 自定义能力 | 可指定输出字段结构、是否保留原始元数据 | 修改输入源内容、写入远程存储 |

### 1.2 适用对象

- **适用**：需要将非结构化内容转为Markdown的开发者、文档工程师、数据分析师
- **不适用**：需要视觉排版还原、需要交互式编辑、需要实时同步的场景


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

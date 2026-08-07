---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: markdownconverter
name: markdownconverter
displayName: 文档格式转换 批处理 样式定制
description: 将 Markdown 文件批量转换为 HTML、PNG 或 PDF，支持自定义样式与模板。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/markdownconverter
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 格式工坊
agent_created: true
trigger_words: ["markdown转换", "md转html", "md转pdf", "md转png", "文档格式转换", "md转图片", "批量转格式"]
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

# Markdown 格式转换器（markdownconverter）

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 功能项 | 说明 | 支持格式 |
|--------|------|----------|
| 单文件转换 | 将单个 .md 文件转为目标格式 | HTML / PNG / PDF |
| 批量转换 | 将指定目录下所有 .md 文件逐一转换 | HTML / PNG / PDF |
| 自定义样式 | 通过 CSS 或主题模板控制输出外观 | 全部格式 |
| 目录结构保留 | 转换时保留源文件的目录层级关系 | 全部格式 |
| 图片资源处理 | 自动识别并处理文档中的本地图片引用 | HTML / PDF |
| 代码高亮 | 对代码块进行语法高亮渲染 | HTML / PDF |

### 1.2 不能做什么

- 不支持将 HTML / PNG / PDF 反向转回 Markdown
- 不支持加密 PDF 的生成（无密码保护功能）
- 不支持对扫描件或图片中的文字进行 OCR 识别
- 不支持实时预览或交互式编辑
- 不支持从远程 URL 直接抓取 Markdown 内容进行转换

### 1.3 适用对象

- 需要将技术文档、README、笔记转为可分享格式的内容创作者
- 需要批量生成项目文档站点的开发人员
- 需要将 Markdown 讲义转为 PDF 或图片用于分发教育工作者
- 需要将 Markdown 报告转为正式格式的商务人士


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

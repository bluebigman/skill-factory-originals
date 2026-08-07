---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: scrapfly-scrapers
name: scrapfly-scrapers
displayName: 网页采集 数据抽取 结构化输出
description: 面向40+主流网站的Python爬虫脚本，将网页数据转为结构化结果。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/scrapfly-scrapers
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Studio
agent_created: true
trigger_words: ["爬虫采集", "网页抓取", "数据抽取", "scraping", "crawler", "结构化输出"]
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

# scrapfly-scrapers 技能文档

## 一、能力边界速查卡

本技能面向需要从网页中批量提取结构化数据的开发者、数据分析师与自动化流程设计者。以下用一页纸说明能做什么、不能做什么。

| 维度 | 说明 |
|------|------|
| **核心能力** | 将用户提供的 URL、HTML 文件或已抓取的文本内容，转换为符合约定 schema 的结构化数据（JSON/CSV） |
| **输入类型** | ① 单个或多个 URL 列表；② 本地 HTML 文件路径；③ 用户直接粘贴的网页正文片段 |
| **输出格式** | JSON 数组（默认）、CSV（可选）、Markdown 表格（可选） |
| **字段识别** | 自动识别标题、正文、发布时间、作者、主图链接、分页链接等 12 个通用字段；针对电商、新闻、论坛三类站点有扩展字段 |
| **批量处理** | 单次最多提交 200 个 URL，超出部分自动分批并提示 |
| **置信度标注** | 每个字段附带 `confidence` 属性（0-1），低于 0.6 的字段自动标记 `[需核实:字段名]` |
| **不能做** | ① 绕过登录墙或验证码；② 处理需要 JavaScript 重度渲染的单页应用（SPA）；③ 采集违反 robots.txt 的站点；④ 对图片/PDF 等非文本内容做 OCR 识别 |
| **适用对象** | 静态或轻动态网页、REST API 返回的 JSON 页面、分页列表页 |


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

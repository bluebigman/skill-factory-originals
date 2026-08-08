---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: autoscraper
name: autoscraper
displayName: 网页采集 数据抽取 结构化清洗
description: 将网页URL或文本自动解析为结构化数据，支持批量与自定义格式。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/autoscraper
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataPilot Studio
agent_created: true
trigger_words: ["爬虫采集", "网页抓取", "数据抽取", "结构化提取", "批量采集"]
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

# autoscraper — 网页数据自动采集与结构化输出

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| 输入 | 用户提供的 URL、HTML 文本、本地文件路径 | 需要登录态的私有系统（无 Cookie/Session 注入） |
| 处理 | 自动识别列表、标题、链接、表格、图片等常见结构 | 复杂 JS 渲染后的动态内容（需配合无头浏览器） |
| 输出 | JSON / CSV / Markdown 表格 / 自定义分隔符文本 | 直接写入数据库或云存储（需用户自行对接） |
| 批量 | 支持多 URL 顺序采集，自动去重 | 分布式并发采集（单机串行） |
| 容错 | 单条失败自动跳过并记录错误原因 | 无限重试（最多 3 次） |

### 1.2 适用对象

- **适用**：静态网页、REST API 返回的 JSON/XML、本地 HTML 文件、RSS 源
- **不适用**：需要交互操作的 SPA 应用、验证码保护的页面、流媒体内容

### 1.3 输入输出规格速查

| 项目 | 规格 |
|------|------|
| 输入来源 | URL（http/https）、文件路径（.html/.txt/.json）、直接粘贴的文本 |
| 输出格式 | `json`（默认）、`csv`、`markdown`、`custom`（自定义分隔符） |
| 字段结构 | 自动推断 + 用户可指定 `fields` 参数覆盖 |
| 置信度标注 | 每个字段附带 `confidence` 值（0.0~1.0），低于 0.6 时标记 `[需核实:字段名]` |


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

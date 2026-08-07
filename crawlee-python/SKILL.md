---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: crawlee-python
name: crawlee-python
displayName: 网页采集 数据抽取 结构化输出
description: 基于Crawlee的Python爬虫技能，将URL或文件转为结构化数据。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/crawlee-python
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Studio
agent_created: true
trigger_words: ["爬虫采集", "网页抓取", "数据抽取", "爬虫", "crawlee", "scraping", "数据采集"]
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

# Crawlee-Python 网页采集与结构化输出 Skill

## 一、能力边界速查卡（一页纸）

| 维度 | 说明 |
|------|------|
| **核心用途** | 将用户提供的 URL、HTML 文件或原始文本，通过 Crawlee 爬虫框架采集后，转换为符合约定 schema 的结构化 JSON 输出 |
| **能做** | ① 单页/多页 URL 抓取与解析；② 本地 HTML/文本文件读取；③ 自动提取标题、正文、链接、表格等常见字段；④ 按用户自定义字段映射输出；⑤ 批量 URL 列表处理；⑥ 输出前字段完整性校验 |
| **不能做** | ① 绕过登录墙/验证码/反爬策略（如 Cloudflare 质询）；② 执行复杂 JavaScript 渲染（需配合 Playwright 插件，本 Skill 默认不启用）；③ 无限深度递归爬取（默认深度 ≤ 3）；④ 对动态加载接口（XHR/Fetch）做逆向；⑤ 保证目标网站结构不变时的长期稳定性 |
| **适用对象** | 静态或轻动态网页、公开 API 返回的 HTML、本地保存的网页快照、RSS/XML 源 |
| **不适用对象** | 需登录的私域数据、强反爬站点、单页应用（SPA）且无 SSR 的站点 |
| **输入限制** | URL 数量 ≤ 50 个/批；单文件 ≤ 5MB；单次任务总超时 ≤ 120 秒 |
| **输出格式** | JSON（默认）/ CSV / Markdown 表格，字段结构由用户指定或使用内置默认 schema |


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

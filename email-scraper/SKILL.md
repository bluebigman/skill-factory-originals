---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: email-scraper
name: email-scraper
displayName: 邮箱采集 网页爬取 邮件挖掘
description: 递归爬取网站页面，自动提取并整理公开邮箱地址。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/email-scraper
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 拾贝工坊
agent_created: true
trigger_words: ["email-scraper", "爬虫采集", "邮箱抓取", "邮件地址收集", "网站邮箱提取", "邮件挖掘"]

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

# email-scraper 技能文档

## 一、能力边界速查卡

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入 | 用户提供的 URL、本地 HTML 文件、纯文本数据 | 无法直接处理 PDF、图片中的邮箱（需先转文本） |
| 爬取 | 递归跟随站内链接，深度可配置（默认 2 层） | 不绕过 robots.txt，不模拟登录态，不处理验证码 |
| 提取 | 识别 `mailto:` 链接、页面正文中的邮箱字符串 | 不识别图片/JS 动态渲染后的邮箱（需配合渲染工具） |
| 输出 | 结构化 JSON、CSV、纯文本列表 | 不自动发送邮件、不做去重后的二次营销 |
| 过滤 | 支持域名白名单/黑名单、正则自定义 | 无法判断邮箱是否有效（不发送验证邮件） |

### 1.2 适用对象

- **适用**：公开联系页、企业官网、学术主页、开源项目 README 中的公开邮箱
- **不适用**：需要登录的私域页面、反爬严格的站点、含大量动态渲染内容的 SPA 应用


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

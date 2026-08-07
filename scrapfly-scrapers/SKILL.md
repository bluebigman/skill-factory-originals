---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: scrapfly-scrapers
name: scrapfly-scrapers
displayName: 网页采集 数据抽取 结构化输出
description: 面向40+主流网站的Python爬虫脚本，将网页数据转为结构化结果。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/scrapfly-scrapers
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Studio
agent_created: true
trigger_words: ["爬虫采集", "网页抓取", "数据抽取", "scraping", "crawler", "数据采集", "页面解析", "--selftest", "--version"]

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

# scrapfly-scrapers — 网页数据采集与结构化输出 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 覆盖范围 |
|--------|------|----------|
| 目标站点采集 | 针对 40+ 主流网站（电商、新闻、社交、招聘、房产等）编写专用爬虫脚本 | 每个站点对应一个独立脚本模块 |
| 数据抽取 | 从 HTML 页面中提取标题、价格、评论、日期、作者、链接等字段 | 支持 CSS 选择器与 XPath 两种定位方式 |
| 结构化输出 | 将抽取结果统一转换为 JSON 格式，字段名与类型保持一致 | 输出 schema 固定，便于下游直接消费 |
| 批量采集 | 支持列表页翻页、详情页遍历、关键词搜索采集 | 内置限速与重试机制 |
| 反爬应对 | 内置 User-Agent 轮换、请求间隔控制、Cookie 保持 | 仅限合法合规站点，不绕过登录鉴权 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不处理登录墙 | 需要账号密码的站点不在覆盖范围内 |
| 不绕过验证码 | 遇到验证码直接返回错误码 `CAPTCHA_DETECTED`，不做破解 |
| 不采集动态渲染页面 | 仅针对服务端渲染的 HTML；SPA 站点需配合无头浏览器（不在本 Skill 范围内） |
| 不提供分布式调度 | 单机串行/并发模式，不包含任务队列与集群管理 |
| 不保证字段完整率 | 目标站点改版或字段缺失时，输出中对应字段为 `null` 或 `[需核实:字段名]` |

### 1.3 适用对象

- 需要定期从公开网站获取结构化数据的开发者
- 做市场调研、竞品分析、舆情监控的数据工程师
- 需要快速搭建采集原型（PoC）的团队


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

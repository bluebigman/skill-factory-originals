---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: firecrawl
name: firecrawl
displayName: 网页采集 数据转换 批量抓取
description: 将网页、文件与URL批量转换为结构化数据，支持搜索与自定义格式输出。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/firecrawl
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Studio
agent_created: true
trigger_words: ["firecrawl", "网页抓取", "爬虫", "数据采集", "网页转结构化", "批量抓取", "URL解析"]
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

# Firecrawl 技能文档

## 一、能力边界速查卡

### 1.1 能做什么

| 序号 | 能力项 | 说明 | 适用场景举例 |
|------|--------|------|--------------|
| 1 | 网页内容抓取 | 从指定 URL 提取正文、标题、元数据 | 新闻采集、竞品监控 |
| 2 | 文件转结构化 | 将 PDF、Word、Excel 等文件解析为 JSON/Markdown | 合同信息抽取、报表汇总 |
| 3 | 批量 URL 处理 | 同时提交多个链接，统一返回结果集 | 整站内容迁移、批量文章归档 |
| 4 | 搜索增强抓取 | 基于关键词搜索后抓取结果页内容 | 市场调研、舆情监测 |
| 5 | 自定义格式输出 | 按用户指定的字段结构返回数据 | 对接业务系统、数据仓库入库 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不处理登录墙 | 需要身份验证的页面无法抓取 |
| 不执行 JavaScript 渲染后的动态内容 | 仅支持服务端渲染页面 |
| 不提供数据清洗服务 | 返回原始提取结果，清洗需用户自行处理 |
| 不保证抓取频率 | 高频请求可能被目标站点限流 |
| 不处理验证码 | 遇到验证码直接返回错误码 |

### 1.3 适用对象

- 需要批量采集公开网页数据的开发者
- 需要将非结构化文档转为结构化数据的数据工程师
- 需要定期监控特定网页内容变化的产品经理


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

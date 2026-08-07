---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: booking-scraper
name: booking-scraper
displayName: 房源采集 数据清洗 结构化输出
description: 将Booking.com房源页面转为结构化数据，支持批量处理与自定义字段。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/booking-scraper
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Studio
agent_created: true
trigger_words: ["booking-scraper", "爬虫采集", "房源抓取", "酒店数据提取", "页面解析"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# Booking.com 房源采集与结构化输出 Skill

## 一、能力边界速查卡

本 Skill 用于将 Booking.com 的房源详情页、搜索结果页或用户提供的 HTML 文件，转换为结构化的 JSON/Markdown 数据。适用于数据调研、竞品分析、价格监控等场景。

| 维度 | 说明 |
|------|------|
| ✅ 能做 | 解析房源名称、地址、评分、价格、设施列表、图片链接、描述文本 |
| ✅ 能做 | 从 URL 直接抓取（需网络可用）或从本地 HTML 文件读取 |
| ✅ 能做 | 批量处理多个 URL/文件，输出统一格式 |
| ✅ 能做 | 自定义输出字段（仅提取用户指定的字段） |
| ✅ 能做 | 对缺失字段标注 `[需核实:字段名]` 占位符 |
| ❌ 不能做 | 绕过登录墙或验证码（仅处理公开可访问页面） |
| ❌ 不能做 | 处理动态加载内容（如地图、实时价格曲线） |
| ❌ 不能做 | 保证数据实时性（以抓取时刻页面为准） |
| ❌ 不能做 | 反爬策略规避（遵守 robots.txt 与网站条款） |

**适用对象**：需要批量获取房源公开信息的分析师、研究者、自动化流程开发者。


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: github-trending-reporter
name: github_trending_reporter
displayName: 开源热榜 周报生成 趋势追踪
description: 自动抓取GitHub Trending，生成结构化周报，支持语言与日期筛选。
version: 1.2.5
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/github-trending-reporter
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: TrendCraft Studio
agent_created: true
trigger_words: ["github trending", "trending 周报", "开源项目周报", "趋势项目汇总", "热榜整理"]
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

# GitHub Trending 周报生成器（Skill 文档）

## 一、能力边界：一页纸速查卡

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| 数据抓取 | 从 GitHub Trending 公开页面提取项目列表 | 访问需要登录的私有仓库或 API 限流后的数据 |
| 字段提取 | 项目名、描述、主语言、Star 数、今日/本周 Star 增量、贡献者数 | 无法获取未在 Trending 页面展示的隐藏指标（如代码提交频率） |
| 筛选过滤 | 按编程语言（Python/JavaScript/Go 等）和日期范围（近 7 天/近 30 天）过滤 | 不支持按仓库大小、许可证类型或组织维度筛选 |
| 输出格式 | 生成 Markdown 周报、CSV 表格、JSON 结构化数据 | 不生成 PDF、PPT 或可视化图表（需借助外部工具） |
| 批量处理 | 一次处理多个日期范围或语言组合的抓取任务 | 不支持实时监控或定时自动推送（需配合调度器） |
| 数据校验 | 抽查比对源页面与输出条目，标记不一致字段 | 无法验证项目描述是否准确反映最新代码状态 |

### 1.2 适用对象

- **开发者**：每周快速了解所在技术栈的热门开源项目
- **技术管理者**：跟踪团队关注领域的生态趋势
- **开源爱好者**：发现值得 star 或参与贡献的新项目
- **内容创作者**：为技术周刊或博客收集素材


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

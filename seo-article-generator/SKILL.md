---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: seo-article-generator
name: seo-article-generator
displayName: SEO文章 关键词研究 内容初稿生成
description: 基于搜索与网页数据，生成有研究依据的SEO文章初稿。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/seo-article-generator
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: ContentForge Studio
agent_created: true
trigger_words: ["SEO文案", "SEO文章", "搜索排名内容", "关键词文章", "内容优化", "关键词研究", "文章初稿", "搜索意图分析"]

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

# SEO 文章生成器（seo-article-generator）

## 一、能力边界速查卡

### 1.1 能做什么

| 能力项 | 说明 | 输入示例 | 输出示例 |
|--------|------|----------|----------|
| 关键词解析 | 从用户提供的关键词中提取核心主题、搜索意图、目标受众 | `"2025年家庭储能电池选购指南"` | 核心主题：家庭储能；意图：选购对比；受众：户主/DIY爱好者 |
| URL 内容抓取 | 抓取公开网页内容，提取结构化信息作为写作素材 | `https://example.com/energy-storage-guide` | 页面标题、H1-H3 层级、关键段落、数据点列表 |
| 文档解析 | 将用户上传的文档（txt/md/pdf）解析为可引用的素材库 | 产品白皮书 PDF | 分章节摘要、关键术语表、可引用数据 |
| 文章结构生成 | 按 SEO 最佳实践生成标题、段落、列表、引用块 | 核心主题 + 关键词列表 | 完整文章大纲（含 H1/H2/H3 层级） |
| 批量处理 | 一次提交多个关键词或 URL，生成多篇大纲 | 5 个关键词 + 3 个参考 URL | 5 份独立文章大纲，每份含引用来源标注 |
| 缺失字段标注 | 对信息不完整的字段输出 `[需核实:字段名]` 占位符 | 无明确数据支撑的统计数字 | `[需核实:2024年市场增长率]` |

### 1.2 不能做什么

| 限制项 | 说明 | 替代方案 |
|--------|------|----------|
| 排名保证 | 不承诺任何搜索排名或流量效果 | 建议结合 Search Console 数据人工优化 |
| 事实核验 | 不替代人工对数据、政策条款的核验 | 输出中标注 `[需核实]` 字段，由使用者确认 |
| 登录内容 | 不处理需要登录权限的网页 | 请用户提供公开可访问的 URL 或文档内容 |
| 非文本格式 | 不生成视频脚本、图文卡片等非文本内容 | 如需要，请另行约定格式规范 |
| 编造数据 | 不虚构统计数字、引用来源或用户评价 | 信息不足时输出占位符，由使用者补充 |

### 1.3 适用对象

- **内容运营人员**：需要快速生成文章初稿，再进行人工润色
- **SEO 专员**：需要基于关键词研究产出结构化内容框架
- **独立站站长**：批量生成产品描述、博客文章初稿
- **内容外包管理者**：为写手提供结构化大纲和素材包


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

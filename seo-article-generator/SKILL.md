---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: seo-article-generator
name: seo-article-generator
displayName: SEO文案 搜索洞察 内容生成
description: 抓取搜索与网页数据，生成有研究依据的SEO文章初稿。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/seo-article-generator
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["SEO文案", "SEO文章", "搜索排名内容", "关键词文章", "内容优化", "seo-article-generator"]

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

# SEO 文案生成器（seo-article-generator）使用手册

## 一、能力边界：一页纸速查卡

本 Skill 用于将「搜索数据 + 网页素材」转化为结构化的 SEO 文章初稿。它不负责排名承诺，只负责产出有据可依的内容底稿。

| 维度 | 说明 |
|------|------|
| **核心输入** | 关键词列表、目标 URL、参考网页链接、用户提供的文本/文件 |
| **核心输出** | 带标题层级、关键词布局、引用来源标注的 Markdown 文章 |
| **处理链路** | 解析输入 → 抓取搜索与网页内容 → 提炼要点 → 生成文章框架与正文 |
| **适用对象** | 内容运营、独立站站长、SEO 初学者、需要批量产出选题初稿的团队 |
| **不适用场景** | 不保证排名结果、不替代人工事实核查、不处理非文本类素材（如图片/视频内容） |

### 能做与不能做

**能做：**
1. 将用户提供的关键词、URL、文档内容解析为结构化输入。
2. 从输入中识别核心主题、目标受众、关键词密度需求。
3. 按预设的文章结构模板（标题、段落、列表、引用）生成输出。
4. 对信息不完整的字段标注 `[需核实:字段名]`，不编造数据。
5. 支持一次提交多个关键词或 URL，批量生成文章大纲。

**不能做：**
1. 不能保证搜索排名或流量效果。
2. 不能替代人工对事实、数据、政策条款的核验。
3. 不能处理需要登录权限的网页内容。
4. 不能生成非文本格式（如视频脚本、图文卡片）——除非用户明确要求并另行约定。


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

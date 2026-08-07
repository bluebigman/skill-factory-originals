---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: wechat-article-pipeline-skill
name: wechat-article-pipeline-skill
displayName: 公众号文章 排版配图 草稿推送
description: 将素材转为公众号文章，完成排版配图与草稿创建。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/wechat-article-pipeline-skill
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Studio
agent_created: true
trigger_words: ["公众号文章", "微信文章排版", "图文排版", "草稿箱", "文章配图", "公众号草稿"]

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

# 微信公众号内容生产流水线 Skill

## 一、能力边界速查卡

本 Skill 面向需要将零散素材（文本、数据表格、网页链接）快速转化为符合公众号发布规范的成品文章的内容创作者、运营人员及 AI Agent。

| 维度 | 说明 |
|------|------|
| ✅ 能做 | 解析用户提供的文本/文件/URL 中的核心信息；将内容重组为公众号文章结构；生成配图规划建议（含尺寸、风格、位置）；输出 HTML 与 Markdown 双格式排版；调用公众号接口创建草稿 |
| ✅ 能做 | 识别原文中的关键数据、引用、结论，并在输出中保留；对信息完整度不足的字段给出置信度提示；支持一次处理多篇文章素材并批量生成草稿 |
| ❌ 不能做 | 无法直接发布文章（仅创建草稿，需人工在公众号后台确认）；不负责配图的实际绘制或版权审核；不替代人工编辑对内容真实性的最终判断 |
| ❌ 不能做 | 不处理涉及用户隐私数据的存储与转发；不生成违反微信公众平台运营规范的内容（如诱导分享、虚假宣传） |

**适用对象**：需要日更或周更的公众号运营者、内容团队、利用 AI 辅助写作的独立创作者。


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

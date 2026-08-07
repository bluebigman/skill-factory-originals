---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: wechat-article-to-md
name: wechat-article-to-md
displayName: 公众号文章 转Markdown 图片下载
description: 抓取微信公众号文章并转为Markdown，自动下载文中图片。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/wechat-article-to-md
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingTool
agent_created: true
trigger_words: ["公众号文章", "微信文章转Markdown", "文章抓取", "wechat article", "公众号转md", "文章备份"]

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

# 微信公众号文章转 Markdown 技能手册

## 一、能力边界（一页纸速查卡）

| 维度 | 说明 |
|------|------|
| **核心任务** | 将微信公众号文章链接转换为结构清晰的 Markdown 文件，并自动下载文章内嵌图片至本地 |
| **输入要求** | 有效的微信公众号文章 URL（`https://mp.weixin.qq.com/s/...` 格式） |
| **输出产物** | 一个 `.md` 文件 + 一个 `images/` 文件夹（存放已下载的图片） |
| **能做** | ① 提取文章标题、作者、发布时间、正文内容；② 将正文中的图片标签转换为本地相对路径引用；③ 保留原文加粗、斜体、引用、代码块等基础格式；④ 处理文章内嵌的二维码图片（默认保留）；⑤ 输出文件命名规则：`标题_日期.md` |
| **不能做** | ① 无法抓取需要关注/验证码才能查看的付费或受限文章；② 不处理文章内的视频、音频资源；③ 不保留原文的复杂 CSS 样式（如背景色、字体大小）；④ 不抓取文章评论区内容；⑤ 不处理非微信公众号域名的链接 |
| **适用对象** | 内容创作者、研究员、知识管理爱好者、需要离线备份公众号文章的个人用户 |


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

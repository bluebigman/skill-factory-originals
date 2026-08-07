---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: wechat-article-to-markdown
name: wechat-article-to-markdown
displayName: 公众号文章 转Markdown 内容提取
description: 抓取微信公众号文章并转换为结构化Markdown，保留关键信息。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/wechat-article-to-markdown
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 墨澜工坊
agent_created: true
trigger_words: ["公众号文章", "微信文章转Markdown", "文章抓取", "内容提取", "网页转MD"]
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

# 微信公众号文章抓取与 Markdown 转换 Skill 文档

## 一、能力边界：一页纸速查卡

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| **输入来源** | 用户直接粘贴的文章正文、分享的链接（mp.weixin.qq.com 域名）、已下载的 HTML 文件、纯文本内容 | 需要登录验证的付费文章、被删除或违规下架的文章、非微信生态的网页（如知乎、CSDN） |
| **内容处理** | 提取标题、作者、发布时间、正文段落、图片链接、代码块、引用块、表格 | 提取评论区内容、阅读量/点赞数等互动数据、文章内嵌视频的播放地址 |
| **格式转换** | 输出标准 Markdown，保留标题层级（H1-H4）、列表、粗斜体、链接、图片引用 | 保留原文的复杂 CSS 样式、自定义字体颜色、背景色、图文混排的精确位置 |
| **批量操作** | 一次处理多个链接（最多 10 个），生成独立文件或合并文件 | 定时自动抓取、监控公众号更新、增量同步 |
| **自定义输出** | 可指定是否包含图片、是否保留原文链接、是否生成目录（TOC） | 输出为 PDF、Word 或 HTML 格式（仅支持 Markdown） |

### 1.2 适用对象

- **内容创作者**：需要将公众号文章迁移到个人博客、知识库或笔记软件
- **研究人员**：收集多篇公众号文章作为参考资料，需要统一格式
- **开发者**：需要将文章内容作为训练数据或文档素材


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

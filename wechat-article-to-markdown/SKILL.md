---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: wechat-article-to-markdown
name: wechat-article-to-markdown
displayName: 公众号文章 结构化转存 内容萃取
description: 抓取微信公众号文章，转换为结构化Markdown，保留标题、作者、正文与图片引用。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/wechat-article-to-markdown
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: content-bridge-studio
agent_created: true
trigger_words: ["公众号文章", "微信文章转Markdown", "文章抓取", "内容提取", "网页转MD", "推文存档", "图文另存"]
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

# 微信公众号文章转 Markdown 操作指南

## 一、能力边界（一页纸速查）

| 维度 | 说明 |
|------|------|
| 能做的事 | 提取公众号文章页面的标题、作者、发布时间、正文段落、图片链接、引用块、代码块 |
| 不能做的事 | 无法绕过微信登录墙、无法抓取付费/加密/已删除文章、无法解析文章内嵌视频/音频文件本身 |
| 输出格式 | 标准 Markdown（.md），图片以 `![描述](URL)` 形式保留原链接 |
| 适用对象 | 需要将公众号内容迁移至笔记软件、博客、知识库的个人或团队 |
| 不适用对象 | 需要批量抓取他人文章用于商业转载、需要下载高清原图、需要保留复杂排版（如卡片样式）的场景 |

**输入要求**：一个可公开访问的微信公众号文章 URL（`https://mp.weixin.qq.com/s/...` 格式）。

**输出产物**：一份结构化的 Markdown 文本，包含 YAML frontmatter（标题、作者、日期）与正文内容。


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

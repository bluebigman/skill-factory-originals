---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: wechat-article-for-ai
name: wechat-article-for-ai
displayName: 公众号文章 Markdown 转换器
description: 将微信公众号文章链接转为结构化 Markdown，支持批量处理与图片本地化。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/wechat-article-for-ai
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本 Skill 由 AI 辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["公众号文章", "wechat article", "微信文章转markdown", "公众号内容提取", "文章抓取", "微信推文转存", "mp.weixin 链接转换"]
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

# 公众号文章 Markdown 转换器（wechat-article-for-ai）

## 一、能力边界（一页纸速查卡）

| 维度 | 说明 |
|------|------|
| ✅ 能做 | 将单个或多个微信公众号文章链接转换为结构化 Markdown 文档 |
| ✅ 能做 | 自动提取标题、作者、发布时间、正文内容 |
| ✅ 能做 | 将正文中的图片下载到本地并替换为相对路径引用 |
| ✅ 能做 | 批量处理多个 URL（每行一个） |
| ✅ 能做 | 对抓取失败的任务自动重试（最多 3 次，间隔 2 秒） |
| ❌ 不能做 | 处理非微信公众号域名的链接（如知乎、CSDN 等） |
| ❌ 不能做 | 绕过微信的访问权限限制（如付费文章、已被删除的文章） |
| ❌ 不能做 | 提取评论区内容、点赞数、阅读量等互动数据 |
| ❌ 不能做 | 将 Markdown 转换回 HTML 或 PDF |
| ❌ 不能做 | 处理需要登录才能访问的公众号文章 |

**适用对象**：内容创作者、AI 训练数据准备人员、知识库管理员、需要批量归档公众号文章的运营人员。


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

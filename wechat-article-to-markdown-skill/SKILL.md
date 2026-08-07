---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: wechat-article-to-markdown-skill
name: wechat-article-to-markdown-skill
displayName: 公众号文章 链接转存 Markdown 归档
description: 输入公众号文章链接，自动抓取正文并保存为本地 Markdown 文件。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/wechat-article-to-markdown-skill
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["公众号文章", "微信文章转Markdown", "链接转文档", "文章归档", "抓取公众号"]

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

# 公众号文章转 Markdown 归档 Skill

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 序号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| 1 | 链接抓取 | 从公众号文章 URL 提取标题、作者、正文、封面图 | `https://mp.weixin.qq.com/s/xxxx` |
| 2 | 正文清洗 | 去除页脚广告、推荐阅读、二维码引导等噪声区块 | 自动识别并剥离 |
| 3 | 图片处理 | 下载正文图片到本地 `assets/` 目录，并在 Markdown 中引用相对路径 | 自动完成 |
| 4 | 结构化输出 | 生成带 YAML frontmatter 的标准 Markdown 文件 | 见 3.3 输出规范 |
| 5 | 批量处理 | 支持一次提交多个链接，逐个生成独立文件 | 每行一个 URL |

### 1.2 不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 付费/加密文章 | 无法抓取需要付费、关注或验证码才能查看的内容 |
| 2 | 已删除文章 | 链接失效或文章被作者删除时，无法恢复 |
| 3 | 非公众号链接 | 仅支持 `mp.weixin.qq.com` 域名的文章页，不支持朋友圈、视频号等 |
| 4 | 排版保真 | 不保证复杂排版（表格、特殊字体、SVG 动效）100% 还原 |
| 5 | 评论与阅读数据 | 不抓取评论区内容、阅读量、点赞数等互动数据 |

### 1.3 适用对象

- 内容运营人员：需要将公众号文章归档到内部知识库
- 研究人员：收集行业文章做文本分析
- 个人用户：备份自己或他人公众号文章到本地笔记


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

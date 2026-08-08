---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ai-blog-article-generator
name: ai-blog-article-generator
displayName: 博客文章 智能创作 内容生成
description: 将素材转化为结构化博客文章，支持多格式输出与置信度标注。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ai-blog-article-generator
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["ai blog article generator", "博客文章生成", "内容创作", "文章写作", "SEO文案", "博客写作", "文章生成器"]

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

# 博客文章智能生成器（ai-blog-article-generator）

## 一、能力边界速查卡

### 1.1 能做与不能做

| 维度 | ✅ 能做 | ❌ 不能做 |
|------|--------|----------|
| 输入处理 | 用户提供的文本、数据表格、URL链接、文件内容 | 主动联网抓取未授权内容、读取本地文件系统 |
| 内容转换 | 将素材整理为结构化博客文章、列表、摘要 | 生成虚构事实、编造数据引用、伪造专家观点 |
| 格式输出 | Markdown、纯文本、HTML片段、JSON结构化数据 | 直接发布到CMS平台、自动排版PDF |
| 信息处理 | 识别关键信息、保留原文核心数据、标注不确定项 | 对未提供的信息做默认假设并写入正文 |
| 批量操作 | 支持多篇素材依次处理、统一格式输出 | 并行处理超过10个任务（受上下文窗口限制） |

### 1.2 适用对象

- **内容运营人员**：需要将产品文档、会议纪要转化为博客草稿
- **SEO专员**：需要围绕关键词生成结构化文章框架
- **技术写作者**：需要将API文档、代码注释整理为教程文章
- **学生研究者**：需要将文献笔记整理为综述性文章

### 1.3 输入输出规格

| 项目 | 规格 |
|------|------|
| 输入来源 | 用户粘贴文本 / 上传文件（txt, md, csv）/ 提供URL |
| 输入大小限制 | 单次不超过 8000 字（超出部分自动截断并提示） |
| 输出格式 | Markdown（默认）/ JSON / 纯文本（通过参数指定） |
| 输出字段结构 | 标题、摘要、正文（分节）、关键词列表、置信度标注 |


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

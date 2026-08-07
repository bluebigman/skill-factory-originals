---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: subtubular
name: subtubular
displayName: 字幕检索 视频元数据 全文搜索
description: 搜索YouTube字幕与视频元数据，支持命令行与图形界面操作。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/subtubular
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["视频字幕", "subtubular", "字幕搜索", "YouTube字幕", "字幕检索"]
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

# subtubular — YouTube 字幕与元数据全文检索

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入 | 用户提供的 YouTube URL、字幕文件（.srt/.vtt）、视频 ID、本地文本文件 | 无法自行抓取未公开或需登录的视频内容 |
| 搜索 | 对字幕文本进行全文关键词检索，支持模糊匹配与短语匹配 | 不支持语义向量检索（如"找关于猫的温馨片段"这类抽象查询） |
| 元数据 | 提取视频标题、频道名、发布时间、时长、观看量等公开字段 | 无法获取点赞/踩、评论内容、弹幕等互动数据 |
| 输出 | 结构化 JSON、CSV、纯文本表格，支持自定义字段筛选 | 不生成视频剪辑、缩略图或任何媒体文件 |
| 批量 | 支持多视频 ID 或 URL 列表的批量处理 | 单次请求上限 100 条，超出需分批 |

### 1.2 适用对象

- **内容研究者**：需要快速定位视频中特定话题出现的时间点
- **字幕翻译者**：需要提取原文与译文对照的片段
- **数据标注团队**：需要为视频内容建立结构化索引
- **普通用户**：想回忆某视频中某句话的上下文

### 1.3 输入输出速览

| 项目 | 说明 |
|------|------|
| 输入来源 | 用户粘贴的 URL、上传的字幕文件、命令行参数 |
| 输出格式 | JSON（默认）、CSV、Markdown 表格 |
| 关键字段 | `video_id`, `title`, `channel`, `timestamp`, `text`, `confidence` |


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

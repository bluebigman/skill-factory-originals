---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: youtube-transcript-api
name: youtube-transcript-api
displayName: 视频字幕提取 内容转写 字幕下载
description: 获取YouTube视频字幕与转写文本的Python工具集。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/youtube-transcript-api
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["视频字幕", "youtube-transcript-api", "字幕下载", "视频转写", "transcript", "subtitles"]
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

# youtube-transcript-api 技能文档

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 序号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 获取视频字幕 | 输入 YouTube 视频 URL 或视频 ID，返回可用字幕列表 |
| 2 | 提取转写文本 | 将字幕内容转为纯文本，支持按时间戳分段 |
| 3 | 多语言支持 | 自动检测并获取不同语言的字幕轨道 |
| 4 | 自动生成字幕 | 当视频无人工字幕时，可尝试获取自动生成的字幕 |
| 5 | 结构化输出 | 返回包含文本、开始时间、持续时间的结构化数据 |

### 1.2 不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不处理非 YouTube 平台 | 仅支持 YouTube 域名下的视频 |
| 2 | 不处理直播流 | 仅支持已发布的视频内容 |
| 3 | 不保证字幕存在 | 部分视频无任何字幕轨道，将返回空结果 |
| 4 | 不处理会员专属视频 | 需要登录权限的视频无法访问 |
| 5 | 不提供翻译服务 | 仅获取原始字幕，不做语言转换 |

### 1.3 适用对象

- 需要批量获取视频字幕做内容分析的研究人员
- 需要将视频内容转为文字稿的编辑人员
- 需要多语言字幕做对比学习的学习者
- 需要将视频内容纳入知识库管理的开发者


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

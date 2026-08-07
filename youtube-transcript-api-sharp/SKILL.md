---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: youtube-transcript-api-sharp
name: youtube-transcript-api-sharp
displayName: 字幕转录 解析提取 批处理
description: 解析YouTube字幕数据，按规范输出结构化转录结果。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/youtube-transcript-api-sharp
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: skill-forge-studio
agent_created: true
trigger_words: ["视频字幕", "youtube transcript api sharp", "字幕转录", "转录解析", "字幕提取"]

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

# YouTube Transcript API Sharp 技能文档

## 一、能力边界速查卡

### 1.1 能做什么

| 序号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 输入解析 | 接受用户提供的字幕文件、URL 或原始文本数据 |
| 2 | 关键信息识别 | 自动提取视频ID、语言代码、时间戳、文本内容等核心字段 |
| 3 | 结构化输出 | 按约定 JSON 格式生成转录结果，含元数据与分段内容 |
| 4 | 置信度标注 | 对自动识别或推断的字段标注置信度等级（高/中/低） |
| 5 | 批量处理 | 支持多视频或多文件的批量转录请求，输出合并结果 |

### 1.2 不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不访问网络 | 本技能不主动请求 YouTube API，仅处理用户提供的数据 |
| 2 | 不翻译内容 | 不提供翻译功能，仅做转录与结构化处理 |
| 3 | 不修正原文字 | 保留原始字幕文本，不做拼写或语法修正 |
| 4 | 不生成字幕 | 不创建新字幕，仅对已有字幕数据进行解析重组 |
| 5 | 不处理音频/视频 | 不进行语音识别或媒体文件解码 |

### 1.3 适用对象

- 需要将 YouTube 字幕数据转为结构化 JSON 的开发者
- 需要批量整理字幕文件的研究人员
- 需要快速提取视频关键信息的运营人员


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

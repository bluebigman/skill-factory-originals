---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: yt-transcripts
name: yt-transcripts
displayName: 视频字幕提取 转录工具 内容获取
description: 从YouTube视频链接提取字幕文本，支持多种格式输出与批量处理。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/yt-transcripts
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林默
agent_created: true
trigger_words: ["视频字幕", "youtube transcript", "yt字幕", "视频转录", "字幕下载", "视频文字提取"]
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

# YouTube 视频字幕提取工具（yt-transcripts）

## 一、能力边界速查卡

### ✅ 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 单视频字幕提取 | 输入 YouTube 视频 URL，返回完整字幕文本 | `https://youtube.com/watch?v=abc123` → 字幕全文 |
| 批量视频处理 | 一次提交多个 URL，按顺序返回各视频字幕 | 3 个链接 → 3 段独立字幕文本 |
| 多语言字幕获取 | 指定语言代码（如 en、zh-Hans、ja）获取对应字幕 | `--lang zh-Hans` 获取中文字幕 |
| 时间戳保留 | 输出可含时间轴标记，便于定位内容 | `[00:12:34] 文本内容` |
| 格式转换输出 | 支持纯文本、SRT、JSON 三种输出格式 | `--format srt` 输出字幕文件格式 |

### ❌ 不能做什么

| 限制项 | 说明 |
|--------|------|
| 非公开视频 | 无法获取未公开或私享视频的字幕 |
| 无字幕视频 | 视频本身未提供任何字幕轨道时无法提取 |
| 音频转写 | 本工具仅提取已有字幕，不进行语音识别转写 |
| 视频下载 | 不提供视频文件下载功能 |
| 实时流媒体 | 不支持直播或未完结视频的字幕获取 |

### 🎯 适用对象

- 内容研究者：需要引用视频中的原话
- 视频创作者：需要参考他人视频的脚本结构
- 语言学习者：对照字幕学习外语表达
- 信息整理者：将视频内容转化为可检索文本


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

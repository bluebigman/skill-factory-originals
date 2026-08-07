---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: auto-subtitles
name: auto-subtitles
displayName: 字幕转录 智能处理 格式转换
description: 将视频字幕转录为结构化文本，支持翻译与格式转换。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/auto-subtitles
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["字幕", "auto subtitles", "转录", "翻译字幕", "字幕处理", "视频字幕"]

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

# 字幕转录与处理 Skill 文档

## 一、能力边界速查卡

### 1.1 能做什么

| 序号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| 1 | 字幕文件解析 | 读取 SRT、VTT、ASS 等常见字幕格式 | `input.srt` |
| 2 | 文本转录整理 | 将非结构化文本按时间轴整理为字幕结构 | 纯文本 + 时间戳 |
| 3 | 多语言翻译 | 将字幕内容翻译为目标语言（需用户指定） | 英→中 |
| 4 | 格式转换输出 | 输出为 SRT / VTT / JSON / Markdown 表格 | 输出格式参数 |
| 5 | 批量处理 | 一次处理多个字幕文件，保持目录结构 | 文件夹路径 |

### 1.2 不能做什么

- 不能从无声视频中凭空生成字幕（需要音频轨道或已有文本）
- 不能自动识别说话人身份（除非输入中已包含角色标记）
- 不能保证翻译的文学性（仅提供字面直译，专业润色需人工复核）
- 不能处理加密或损坏的文件（需用户提供可读文件）

### 1.3 适用对象

- 视频创作者需要为内容添加字幕
- 学习者需要将外语视频转录为可读文本
- 开发者需要将字幕转换为结构化数据（JSON）供程序调用
- 翻译人员需要快速获取字幕初稿


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

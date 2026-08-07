---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: meetily
name: meetily
displayName: 会议纪要 实时转写 隐私保护
description: 隐私优先的AI会议助手，支持本地实时转写、说话人分离与纪要生成。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/meetily
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["会议纪要", "meeting minutes", "实时转写", "说话人分离", "会议记录"]
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

# meetily — 隐私优先的 AI 会议助手 Skill 文档

## 1. 能力边界（一页纸速查卡）

### 1.1 能做什么

| 编号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| C1 | 音频/视频文件转写 | 将本地音视频文件转为带时间戳的文本 | `meeting.wav`, `recording.mp4` |
| C2 | 实时语音转写 | 通过麦克风捕获现场语音并实时输出文本 | 现场会议、访谈 |
| C3 | 说话人分离（Diarization） | 区分不同发言人的语音片段并标注 | 多人会议录音 |
| C4 | 会议纪要结构化生成 | 从转写文本中提取议题、决议、待办事项 | 转写文本或文件 |
| C5 | 本地模型推理（Ollama） | 使用 Ollama 运行本地大模型完成摘要/要点提取 | 转写文本 + Ollama 模型名 |

### 1.2 不能做什么

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 云端处理 | 所有处理均在本地完成，不依赖云端 API |
| L2 | 实时翻译 | 不支持跨语言实时翻译，仅支持原文转写 |
| L3 | 视频画面分析 | 不处理视频帧内容，仅处理音轨 |
| L4 | 自动会议日程管理 | 不负责日历同步、会议邀请等事务 |
| L5 | 非语音输入处理 | 不支持图片、PPT 等视觉内容的语义理解 |

### 1.3 适用对象

- 需要本地化、隐私敏感场景的会议记录人员
- 使用 Ollama 等本地模型工具的技术用户
- 需要快速从录音中提取结构化信息的团队助理


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

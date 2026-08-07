---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: subtitles-generator
name: subtitles-generator
displayName: 视频字幕 转录提取 时间轴对齐
description: 从视频链接提取字幕，生成带时间轴的转录文本。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/subtitles-generator
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["视频字幕", "字幕生成", "转录文本", "视频转文字", "字幕提取"]
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

# 视频字幕生成器（subtitles-generator）

## 一、能力边界：一页纸速查卡

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| 输入类型 | 视频文件路径、公开视频 URL、本地音频文件 | 加密视频、需登录的会员视频、直播流 |
| 输出格式 | SRT、VTT、纯文本 TXT、JSON（含时间轴） | 烧录字幕到视频画面（硬字幕） |
| 语言支持 | 中、英、日、韩、法、德、西（自动检测） | 小语种方言、混合代码切换的精准识别 |
| 处理能力 | 单文件 ≤ 2 小时，批量 ≤ 10 个文件 | 实时流媒体、超长视频（>2h）分段处理 |
| 附加功能 | 说话人区分（双人对话）、静音段跳过 | 情感分析、语义摘要、翻译 |

### 1.2 适用对象

- **内容创作者**：为短视频、播客、课程视频添加字幕
- **研究者**：将访谈、讲座视频转为可检索文本
- **开发者**：需要结构化字幕数据（JSON）用于二次开发
- **普通用户**：观看无字幕外语视频时获取辅助文本

### 1.3 输入输出速查

| 项目 | 说明 |
|------|------|
| 输入来源 | 本地文件路径、http(s) 视频直链、youtube/bilibili 等平台分享链接 |
| 输出目录 | 默认与输入文件同目录，可通过 `--output-dir` 指定 |
| 时间轴精度 | 毫秒级（SRT 标准格式） |
| 置信度阈值 | 低于 0.6 的片段会标注 `[低置信度]` 前缀 |


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: anime-dl
name: anime-dl
displayName: 动漫资源采集 链接解析 批量处理
description: 将用户提供的动漫相关链接或数据，转换为结构化、可复用的规范输出。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/anime-dl
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["anime-dl", "动漫下载", "动漫采集", "番剧链接处理", "动漫资源整理"]
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

# anime-dl 技能文档

## 一、能力边界速查卡

本技能用于处理用户提供的动漫相关链接、文件或原始数据，将其转化为结构化的输出结果。以下表格明确列出本技能的能力范围。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入处理 | 解析 URL、文本片段、文件路径中的关键信息 | 无法主动访问互联网或抓取实时网页内容 |
| 信息提取 | 识别标题、集数、画质、字幕组、发布时间等字段 | 无法识别图片或视频中的非文字信息 |
| 格式转换 | 将非结构化文本转为 JSON / Markdown 表格 / CSV | 无法生成压缩包或二进制文件 |
| 批量操作 | 一次处理多条记录，保持字段一致性 | 无法自动下载或保存文件到本地磁盘 |
| 置信度标注 | 对不确定字段标注 `[需核实:字段名]` | 不会编造缺失信息或猜测模糊内容 |

**适用对象**：需要整理动漫资源链接、归档番剧信息、批量格式化资源列表的个人或学习用途场景。


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

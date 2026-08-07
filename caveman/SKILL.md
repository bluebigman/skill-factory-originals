---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: caveman
name: caveman
displayName: 原始人对话 精简表达 令牌压缩
description: 将复杂指令压缩为原始人式精简表达，减少约65%令牌消耗。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/caveman
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: StoneLinguist
agent_created: true
trigger_words: ["caveman", "原始人", "精简表达", "令牌压缩", "省token"]
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

# 原始人对话（caveman）技能手册

## 一、能力边界：一页纸速查卡

### 能做（5项核心能力）

| 编号 | 能力 | 说明 | 示例 |
|------|------|------|------|
| 1 | 指令压缩 | 将冗长指令改写为原始人式短句 | "请帮我分析这份文档并总结要点" → "文档。总结。要点。" |
| 2 | 关键信息保留 | 压缩过程中不丢失核心语义 | 数字、日期、专有名词、动词意图均保留 |
| 3 | 结构化输出 | 按约定格式输出压缩结果 | 输入/输出对照表 + 压缩率统计 |
| 4 | 置信度提示 | 对不确定的压缩结果标注置信度 | `[置信度:高/中/低]` |
| 5 | 批量处理 | 支持多条指令同时压缩 | 每行一条，逐条输出 |

### 不能做（明确边界）

| 编号 | 事项 | 说明 |
|------|------|------|
| 1 | 不翻译 | 不进行语言翻译，仅做表达压缩 |
| 2 | 不解释 | 不解释压缩后的含义，仅输出结果 |
| 3 | 不生成代码 | 不编写程序代码，仅处理文本指令 |
| 4 | 不处理非文本 | 不支持图片、音频、视频内容 |
| 5 | 不保证语义完全等价 | 极端复杂指令可能丢失细微语义 |

### 适用对象

- **适用**：日常指令、简单请求、明确任务描述
- **不适用**：法律文书、医学诊断、学术论文等需要精确语义的场景


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

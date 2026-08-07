---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: chronic
name: chronic
displayName: 日期解析 自然语言 时间转换
description: 将自然语言日期描述解析为结构化时间数据，支持多种格式与批量处理。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/chronic
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 时序工坊
agent_created: true
trigger_words: ["chronic", "日期解析", "自然语言日期", "时间转换", "日期识别", "parse date"]
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

# Chronic 自然语言日期解析 Skill 文档

## 一、能力边界速查卡

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入类型 | 用户直接提供的文本、文件内容、URL 指向的文本 | 二进制文件、图片中的文字（需先 OCR） |
| 解析范围 | 英文自然语言日期描述（如 "next tuesday"、"3 days ago"） | 非英文日期表达、时区转换计算 |
| 输出格式 | 结构化时间对象（年/月/日/时/分/秒）、自定义格式字符串 | 直接生成日历事件、自动设置提醒 |
| 批量处理 | 支持多条日期描述批量解析 | 流式处理超大数据集（建议分块） |
| 自定义能力 | 可指定参考时间（now）、时区偏移、输出格式模板 | 修改 Chronic 核心解析逻辑 |

### 1.2 适用对象

- 需要从用户输入中提取时间信息的开发者
- 构建命令行工具、聊天机器人、任务管理应用的技术人员
- 处理日志文件、文本记录中时间戳的运维工程师


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

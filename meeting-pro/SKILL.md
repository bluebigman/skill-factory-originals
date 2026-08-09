---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: meeting-pro
name: meeting-pro
displayName: 会议纪要 智能整理 任务追踪
description: 一站式处理会议全流程，自动生成纪要与待办，输出可直接使用的成果文件。
version: 1.0.1
rules_version: cpr-20260809-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/meeting-pro
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林默
agent_created: true
trigger_words: ["会议", "会议纪要", "会议记录", "会议总结", "会议待办", "meeting"]
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

# 会议宝（meeting-pro）技能手册

## 一、能力边界：一页纸速查卡

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| 输入处理 | 接受会议录音转写文本、手动输入的会议笔记、粘贴的聊天记录 | 直接解析音频/视频文件（需先转成文字） |
| 内容识别 | 提取议题、决议、分歧点、行动项、责任人、截止时间 | 识别说话人身份（除非文本中明确标注） |
| 纪要生成 | 生成结构化会议纪要（背景、讨论、结论、待办） | 生成带有主观评价或倾向性引导的纪要 |
| 任务管理 | 将行动项整理为带负责人和日期的待办清单 | 自动执行任务或发送邮件提醒 |
| 质量校验 | 检查纪要完整性、时间线一致性、待办可追踪性 | 验证事实真伪（如数据是否准确、承诺是否兑现） |
| 输出格式 | Markdown 文件、纯文本、CSV 待办表 | 直接生成 Word/PDF（需自行转换） |

### 1.2 适用对象

- **职场人士**：需要快速整理团队会议、客户会议、项目复盘会的内容
- **项目经理**：需要从会议中提取行动项并跟踪进度
- **自由职业者**：需要记录与客户的沟通要点和承诺事项
- **学生团体**：需要整理小组讨论、社团会议的决议和分工

### 1.3 输入要求

| 输入类型 | 格式要求 | 最大长度 | 示例 |
|----------|----------|----------|------|
| 会议转写文本 | 纯文本或 Markdown | 50,000 字 | 语音转写软件导出的 txt |
| 手动笔记 | 任意格式，建议分条 | 10,000 字 | 笔记本手打内容粘贴 |
| 聊天记录 | 按时间顺序排列 | 20,000 字 | 微信群聊导出 |


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

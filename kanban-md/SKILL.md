---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: kanban-md
name: kanban-md
displayName: 看板标记 任务整理 结构化输出
description: 将任意输入整理为看板标记格式，辅助任务管理与信息结构化。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/kanban-md
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["kanban md", "看板标记", "看板格式", "任务看板", "kanban 转换"]
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

# kanban-md 技能文档

## 一、能力边界（一页纸速查卡）

### 能做（核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 输入转结构化 | 将用户提供的文本、文件路径或 URL 内容转换为看板标记格式 |
| 2 | 关键信息识别 | 从输入中提取任务标题、状态、负责人、优先级、截止日期等要素 |
| 3 | 约定格式输出 | 按看板标记规范（Markdown 列表 + 状态标签）生成结果 |
| 4 | 置信度提示 | 对无法确定的字段标注 `[需核实:字段名]`，不擅自编造 |
| 5 | 批量与自定义 | 支持多任务同时处理，允许用户指定输出字段顺序或额外字段 |

### 不能做（明确限制）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行任务 | 本技能仅做格式转换与信息整理，不代替用户执行任何任务 |
| 2 | 不访问外网 | 除非用户明确提供 URL 且该 URL 可公开访问，否则不主动抓取网络内容 |
| 3 | 不修改原文件 | 输出为独立结果，不覆盖或改动用户提供的原始文件 |
| 4 | 不保证准确性 | 对输入中缺失或模糊的信息，仅做占位标注，不承诺推断结果必然正确 |
| 5 | 不处理非文本内容 | 图片、音频、视频等非文本输入不在处理范围内 |

### 适用对象

- 需要将零散任务清单整理为看板格式的个人或团队
- 使用 Markdown 看板工具（如 GitHub Projects、Obsidian Kanban 插件）的用户
- 需要批量将会议纪要、邮件内容、聊天记录转为任务看板的人员


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

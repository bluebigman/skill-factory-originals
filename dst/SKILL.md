---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: dst
name: dst
displayName: 任务清单 待办管理 效率工具
description: 解析用户输入的待办事项，生成结构化任务清单，支持批量导入与格式转换。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/dst
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 流云工坊
agent_created: true
trigger_words: ["dst", "todo", "待办", "任务清单", "待办事项", "todo-list"]
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

# dst — 待办事项解析与结构化输出 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 编号 | 能力项 | 说明 |
|------|--------|------|
| C1 | 文本解析 | 从用户提供的自然语言、文件内容或 URL 中提取待办事项 |
| C2 | 关键信息识别 | 识别任务标题、优先级、截止日期、标签、负责人等字段 |
| C3 | 结构化输出 | 按约定的 JSON / Markdown 格式生成任务清单 |
| C4 | 置信度标注 | 对每个字段标注解析置信度（高/中/低） |
| C5 | 批量处理 | 支持一次输入多条任务，自动拆分与归类 |

### 1.2 不能做什么

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行任务 | 仅解析与格式化，不连接任何外部待办系统（如 Todoist、Trello） |
| L2 | 不推断隐含任务 | 输入中未明确提及的事项不会自动补全 |
| L3 | 不处理非文本输入 | 不支持图片、音频中的任务提取 |
| L4 | 不保证语义完美 | 对模糊表述（如"尽快"）只做标记，不猜测具体日期 |

### 1.3 适用对象

- 需要快速将零散笔记转为结构化清单的个人用户
- 需要批量导入任务到其他工具的开发人员
- 希望统一任务格式的团队协作场景


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

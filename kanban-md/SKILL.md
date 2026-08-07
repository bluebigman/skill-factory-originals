---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: kanban-md
name: kanban-md
displayName: 任务看板 结构化整理 信息编排
description: 将任意输入整理为看板标记格式，辅助任务管理与信息结构化。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/kanban-md
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Studio
agent_created: true
trigger_words: ["kanban md", "看板标记", "看板格式", "任务看板", "kanban 转换", "卡片视图", "列式管理"]
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

# kanban-md — 任务看板标记转换器

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 文本转看板 | 将自由文本、列表、会议纪要整理为看板 Markdown 结构 | 把"待办：买牛奶、写周报"转为 `## 待办` 列下的卡片 |
| 列结构识别 | 自动识别输入中的分类词（如"待办/进行中/已完成"）作为看板列 | 输入含"进行中"字样 → 生成对应列 |
| 卡片元数据 | 为卡片附加优先级、负责人、截止日期等标记 | `[高] 修复登录bug @张三 (2025-06-30)` |
| 多级嵌套 | 支持卡片内子任务列表 | `- [ ] 子任务1` 缩进在卡片下方 |
| 看板合并 | 将多个输入片段合并为一个看板文件 | 拼接不同来源的待办事项 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行任务 | 仅生成标记文本，不连接任何待办软件 API |
| 不智能排序 | 不自动判断优先级，仅按输入顺序或显式标记排列 |
| 不校验日期 | 不验证截止日期是否过期或格式是否合法 |
| 不生成图表 | 不输出 HTML/CSS/JS 看板视图，仅纯 Markdown |
| 不处理图片 | 不识别截图或 OCR 内容 |

### 1.3 适用对象

- 需要快速将零散想法整理为看板结构的个人
- 使用 Markdown 看板工具（如 Obsidian、VS Code 插件、GitHub Projects）的团队
- 会议记录后需要结构化输出的参会者
- 产品经理、项目经理、开发者、运营人员


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: pm-manager
name: pm-manager
displayName: 项目管理 优先级决策 任务治理
description: 将零散输入转化为结构化任务清单，辅助AI代理确定下一步修复动作。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/pm-manager
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["pm-manager", "pm manager", "项目管理", "任务治理", "优先级排序", "下一步行动"]
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

# pm-manager — 本地项目治理技能包

## 一、能力边界（一页纸速查卡）

### 1.1 本技能能做什么

| 编号 | 能力项 | 说明 | 输入示例 | 输出示例 |
|------|--------|------|----------|----------|
| C1 | 输入结构化 | 将用户提供的文本、文件路径或URL内容转换为统一格式的任务条目 | 一段会议纪要文本 | 结构化任务列表（JSON/Markdown表格） |
| C2 | 关键信息提取 | 从原始输入中识别任务描述、责任人、截止时间、依赖关系、优先级线索 | 含"尽快""阻塞""下周三"等词汇的文本 | 字段化任务对象 |
| C3 | 格式约定输出 | 按用户指定或默认模板生成输出（Markdown表格、JSON、CSV） | `--format json` | 合法JSON字符串 |
| C4 | 置信度标注 | 对不确定的字段值标注置信度等级（高/中/低） | 模糊日期"下周" | `due_date: "2025-04-16", confidence: "medium"` |
| C5 | 批量处理 | 支持一次处理多个输入源（多文件、多URL、混合输入） | 三个文件路径 + 一段文本 | 合并后的任务总表 |

### 1.2 本技能不能做什么

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行任务 | 只做规划与排序，不实际修改代码、发送消息或操作外部系统 |
| L2 | 不推断缺失信息 | 输入中未明确的信息，输出 `[需核实:字段名]` 占位符，不猜测 |
| L3 | 不评估业务价值 | 优先级排序仅基于输入中显式声明的权重或依赖关系，不主观判断业务重要性 |
| L4 | 不处理二进制文件 | 仅支持文本类输入（.md, .txt, .json, .csv, .yaml, URL页面内容） |
| L5 | 不保证完整性 | 输出质量取决于输入质量；输入缺失关键信息时，输出结果可能不完整 |

### 1.3 适用对象

- **AI编码代理**：需要维护本地任务清单、决定下一步开发动作的场景
- **个人开发者**：手头有零散笔记、待办事项，需要整理成结构化任务列表
- **小型团队**：共享一份本地任务治理文件（如 `.pm/tasks.md`），需要统一格式


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

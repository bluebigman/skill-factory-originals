---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: todo-cli
name: todo-cli
displayName: 待办清单 命令行 任务管理
description: 命令行工具，将输入数据解析为结构化待办事项并输出。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/todo-cli
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Ling
agent_created: true
trigger_words: ["todo cli", "待办清单", "任务管理", "todo list", "命令行待办"]
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

# todo-cli Skill 文档

## 一、能力边界（一页纸速查卡）

### 能做（5项核心能力）

| 序号 | 能力项 | 说明 | 示例 |
|------|--------|------|------|
| 1 | 数据解析 | 将用户提供的文本、文件路径或 URL 内容解析为结构化数据 | `todo cli parse ./tasks.txt` |
| 2 | 关键信息提取 | 从非结构化文本中识别任务描述、优先级、截止日期等要素 | 从"周五前完成报告（高优先级）"提取出 `{task: "完成报告", due: "周五", priority: "高"}` |
| 3 | 格式化输出 | 按约定格式（JSON/CSV/表格）输出结果 | `todo cli --format json` |
| 4 | 置信度标注 | 对自动推断的字段标注置信度，不确定时使用占位符 | `{due: "[需核实:截止日期]"}` |
| 5 | 批量处理 | 支持一次处理多个条目，并支持自定义输出模板 | `todo cli --batch ./tasks/` |

### 不能做（明确边界）

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行任务 | 仅解析和管理待办数据，不负责提醒、调度或执行任务 |
| 2 | 不访问私有数据 | 不主动抓取需要认证的 URL 或本地私有文件，需用户显式提供 |
| 3 | 不保证语义理解 | 对模糊表达（如"尽快"）不强行推断具体日期，会标注置信度 |
| 4 | 不修改原始文件 | 所有操作均为读取和输出，不写回源文件 |
| 5 | 不支持自然语言对话 | 仅处理命令行参数和结构化输入，不提供交互式问答 |

### 适用对象

- 需要快速将零散笔记整理为待办清单的个人用户
- 需要批量导入任务数据的团队协作场景
- 需要将待办数据接入其他自动化流程的开发者


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: awesome-copilot-agents
name: awesome-copilot-agents
displayName: 智能体资源导航 清单整理 链接归档
description: 将GitHub智能体资源链接整理为结构化清单，支持检索与导出。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/awesome-copilot-agents
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: ResourceArchitect
agent_created: true
trigger_words: ["awesome-copilot-agents", "copilot agents 清单", "智能体资源导航", "GitHub 指令整理", "agent 列表汇总", "智能体链接归档", "资源清单生成"]
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

# 智能体资源导航 · 清单整理与归档 Skill

## 一、能力边界（一页纸速查卡）

| 维度 | 说明 |
|------|------|
| **核心能力** | 从用户提供的 URL 或文本中提取资源名称、链接、简介；按资源类型自动归类；识别并合并重复条目；对不确定信息标注占位符；输出 Markdown 表格或 JSON 格式 |
| **输入要求** | 至少包含一个有效 URL 或一段包含 GitHub 链接的文本；建议同时提供资源名称或简介，否则将标注 `[需核实:名称]` |
| **输出格式** | Markdown 表格（默认）或 JSON（通过 `--format json` 指定） |
| **适用对象** | 维护个人收藏夹的开发者、整理团队知识库的技术负责人、需要快速归档大量链接的研究人员 |
| **不处理** | 不访问网络抓取页面内容；不自动生成资源简介；不判断资源质量优劣；不处理非 GitHub 链接（如 GitLab、Bitbucket 等，将标注 `[需核实:平台]` 并跳过归类） |
| **边界值** | 单次处理上限 200 条资源；单条简介长度上限 200 字符（超出截断并标注 `[已截断]`）；重复判定基于 URL 完全匹配（忽略末尾斜杠） |


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

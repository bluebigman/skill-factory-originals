---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: awesome-copilot-agents
name: awesome-copilot-agents
displayName: 智能体资源导航 清单整理与检索
description: 将 GitHub 智能体资源链接整理为结构化清单，支持检索与导出。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/awesome-copilot-agents
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["awesome-copilot-agents", "copilot agents 清单", "智能体资源导航", "GitHub 指令整理", "agent 列表汇总"]
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

# awesome-copilot-agents 技能手册

## 一、能力边界速查卡

本技能用于将散落的 GitHub 智能体资源（指令、提示词、技能包、MCP 服务等）整理为结构化清单，并提供检索与导出能力。

| 维度 | 说明 |
|------|------|
| **输入** | 用户提供的 URL、文件路径、粘贴的文本内容 |
| **输出** | 结构化 Markdown 清单，含分类、描述、来源链接 |
| **处理方式** | 解析 → 分类 → 去重 → 标注置信度 → 输出 |
| **适用对象** | 开发者、技术调研者、AI 工具爱好者 |

### 能做（5 项核心能力）

1. **资源解析**：从用户提供的 URL 或文本中提取资源名称、链接、简介。
2. **自动分类**：按资源类型（指令/提示词/技能/MCP/其他）进行归类。
3. **信息去重**：识别重复条目，合并相同资源并保留最早来源。
4. **置信度标注**：对无法确认的信息标注 `[需核实:字段]`，不编造内容。
5. **批量导出**：支持将整理结果输出为 Markdown 表格或 JSON 格式。

### 不能做（明确边界）

- 不主动抓取互联网内容，仅处理用户明确提供的数据。
- 不判断资源质量优劣，仅做客观整理。
- 不修改原始资源内容，仅做结构化呈现。
- 不保证资源链接长期有效，链接有效性需用户自行验证。


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

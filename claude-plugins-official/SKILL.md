---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: claude-plugins-official
name: claude-plugins-official
displayName: 插件目录检索 官方源 质量筛选
description: 检索并筛选 Anthropic 官方维护的高质量 Claude Code 插件目录。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/claude-plugins-official
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Ling
agent_created: true
trigger_words: ["claude plugins official", "官方插件目录", "插件检索", "官方插件列表", "插件筛选"]
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

# Claude Plugins Official 技能文档

## 一、能力边界速查卡

本技能面向需要从 Anthropic 官方插件目录中查找、筛选、评估插件的开发者或技术决策者。它帮助你将"找插件"这个模糊需求，转化为结构化的插件清单与推荐结论。

| 维度 | 说明 |
|------|------|
| **输入** | 用户提供的插件名称、功能描述、使用场景、技术栈要求、关键词 |
| **输出** | 结构化插件清单（含名称、功能摘要、适用场景、置信度标注） |
| **核心操作** | 解析需求 → 匹配目录 → 筛选排序 → 输出清单 |

**能做：**
- 根据用户描述的功能需求，从官方插件目录中匹配候选插件
- 对插件适用性给出分级评估（高/中/低匹配）
- 输出结构化清单，包含插件名称、用途摘要、匹配理由
- 在信息不足时明确标注缺失字段，不臆造插件信息
- 支持按技术栈、场景、插件类型等多维度筛选

**不能做：**
- 不提供插件的安装命令或配置教程
- 不评价插件的代码质量或维护活跃度（目录中未标注的信息不推测）
- 不推荐非官方来源的插件
- 不生成插件使用示例代码
- 不保证目录中所有插件均适配用户的特定环境

**适用对象：** 需要在 Claude Code 环境中选用官方插件的开发者、技术选型评估人员、自动化流程集成者。


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

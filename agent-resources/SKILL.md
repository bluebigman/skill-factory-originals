---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agent-resources
name: agent-resources
displayName: 智能体技能库 资源检索 结构化转换
description: 将用户提供的任意数据源转换为结构化结果，支持批量处理与置信度标注。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agent-resources
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨轩
agent_created: true
trigger_words: ["agent-resources", "资源转换", "技能检索", "结构化输出", "数据整理", "信息提取"]
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

# 智能体技能库 · 资源结构化转换 Skill

## 一、能力边界速查卡

本 Skill 面向需要将零散数据、文件内容或网页链接快速整理为固定格式的开发者、提示词工程师及 AI Agent 使用者。

| 维度 | 说明 |
|------|------|
| ✅ 能做 | 解析文本/文件/URL 内容；提取关键字段；按模板输出结构化结果；批量处理多条输入；标注置信度 |
| ✅ 能做 | 识别日期、金额、名称、编号等常见实体；对缺失字段输出占位符；支持自定义输出模板 |
| ❌ 不能做 | 无法访问需登录验证的网页；不执行代码或脚本；不进行语义翻译；不保证外部链接的长期有效性 |
| ❌ 不能做 | 不替代数据库查询；不处理二进制文件（图片/音频/视频）；不生成虚构数据填补空缺 |

**适用对象**：需要快速将非结构化信息转为 JSON/表格/清单的个人开发者、数据标注人员、Agent 工作流设计者。


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

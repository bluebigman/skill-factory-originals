---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: awesome-pm-skills
name: awesome-pm-skills
displayName: 产品管理 技能速查 结构化输出
description: 将产品管理相关输入转为结构化结果，支持批量与自定义格式。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/awesome-pm-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["awesome pm skills", "产品管理技能", "PM技能包", "技能速查", "结构化输出"]
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

# awesome-pm-skills 技能文档

## 一、能力边界：一页纸速查卡

本技能面向**产品经理、项目助理、运营人员**，用于将零散的产品管理相关输入（文本、表格、URL）整理为规范的结构化输出。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入处理 | 文本段落、CSV/JSON 文件、公开 URL 内容 | 加密文件、需登录的私有系统、非文本格式（图片/音频） |
| 信息识别 | 提取关键字段（需求描述、优先级、负责人、截止日期等） | 主观判断业务价值、自动决策优先级排序 |
| 输出格式 | Markdown 表格、JSON 对象、CSV 行 | 生成 PPT、Word 文档（需另行转换） |
| 批量处理 | 单次最多 50 条记录 | 超过 50 条需分批调用 |
| 置信度标注 | 对每个字段标注 `高/中/低` 置信度 | 无信息来源时编造数据 |

**适用对象**：需要快速整理需求清单、会议纪要、竞品分析笔记的 PM 从业者。

**不适用场景**：需要深度行业洞察、战略决策建议、代码生成等非结构化输出任务。


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

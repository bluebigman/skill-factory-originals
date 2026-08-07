---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: claude-skills
name: claude-skills
displayName: 技能研习 规范流程 学习参考
description: 面向学习与参考场景，提供规范、可复用的技能处理流程与输出。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/claude-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林默
agent_created: true
trigger_words: ["claude skills", "技能学习", "技能参考", "技能处理", "技能规范"]
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

# 技能研习与规范处理指南

## 一、能力边界速查卡

本技能面向**学习与参考用途**，帮助用户将输入的数据、文件或链接，转化为结构清晰、标注完整的结果。以下是能力边界一览：

| 维度 | 说明 |
|------|------|
| ✅ 能做 | 解析用户提供的文本、文件内容或 URL 指向的信息 |
| ✅ 能做 | 提取关键字段，按约定结构重组输出 |
| ✅ 能做 | 对不确定信息标注置信度，不强行编造 |
| ✅ 能做 | 支持批量输入（多条记录依次处理） |
| ✅ 能做 | 根据用户指定格式（如 JSON / Markdown 表格）输出 |
| ❌ 不能做 | 访问需登录鉴权的私有系统或付费墙内容 |
| ❌ 不能做 | 对输入内容进行事实核验（仅做格式转换与提取） |
| ❌ 不能做 | 生成超出输入信息范围的推测性结论 |
| ❌ 不能做 | 替代专业法律、医疗、财务等领域的正式意见 |

**适用对象**：需要将零散信息整理为结构化结果的学习者、研究者、文档整理人员。


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

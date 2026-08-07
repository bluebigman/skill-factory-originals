---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: napkin
name: napkin
displayName: 项目备忘 错误记忆 经验沉淀
description: 为项目仓库提供持久化错误记忆与经验备忘的轻量级技能。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/napkin
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["napkin", "备忘", "错误记录", "经验沉淀", "项目记忆"]
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

# napkin — 项目错误记忆与经验备忘技能

## 一、能力边界：速查卡

本技能的核心定位是：**为每个代码仓库维护一份轻量级的 Markdown 备忘文件，记录项目开发中反复出现的错误、踩坑经验与关键决策，让 AI 助手在后续会话中能快速调取这些记忆，避免重复犯错。**

### 1.1 能做（核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 错误记录 | 将用户描述的错误现象、根因、解决方案写入仓库内的备忘文件 |
| 2 | 经验提取 | 从对话中识别值得沉淀的经验教训，主动建议记录 |
| 3 | 记忆检索 | 根据当前任务上下文，检索并展示相关历史错误记录 |
| 4 | 备忘维护 | 支持查看、追加、更新、清理备忘条目 |
| 5 | 自检与版本 | 提供 `--selftest` 校验功能完整性和 `--version` 查看版本号 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不替代文档 | 不负责生成项目正式文档，只做轻量级错误备忘 |
| 2 | 不自动执行 | 不会在未经用户确认的情况下自动写入或修改备忘文件 |
| 3 | 不跨仓库共享 | 每个仓库的备忘文件独立存在，不跨项目同步 |
| 4 | 不存储敏感信息 | 不记录密码、密钥、令牌等敏感凭据 |
| 5 | 不保证完整覆盖 | 只记录用户告知或对话中明确呈现的错误，不主动扫描代码 |

### 1.3 适用对象

- 长期维护的代码仓库，且 AI 助手会多次参与开发
- 团队协作中需要共享踩坑经验的场景
- 个人项目中希望减少重复调试时间的开发者


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

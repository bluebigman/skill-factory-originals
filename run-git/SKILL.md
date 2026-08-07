---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: run-git
name: run-git
displayName: Git操作 代码管理 版本控制
description: 提供Git日常操作的结构化处理流程与规范输出，辅助代码版本管理。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/run-git
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinOps
agent_created: true
trigger_words: ["run git", "git操作", "代码管理", "版本控制", "git命令"]
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

# run-git 技能文档

## 一、能力边界速查卡

本技能面向需要执行 Git 日常操作但希望获得规范化流程指引的开发者、运维人员及技术学习者。它提供的是操作流程、命令模板和输出规范，而非替代 Git 本身。

| 能力维度 | 说明 |
|---------|------|
| ✅ 能做 | 解析用户输入的 Git 操作需求，输出对应命令序列与执行步骤 |
| ✅ 能做 | 将用户提供的仓库状态、报错信息映射为可执行的排查路径 |
| ✅ 能做 | 按约定结构输出操作摘要、风险提示与结果确认清单 |
| ✅ 能做 | 对信息不完整的请求，标注缺失字段并请求补充 |
| ✅ 能做 | 支持批量场景（如多分支操作）的流程拆解 |
| ❌ 不能做 | 直接执行 Git 命令（本技能仅提供指令与流程） |
| ❌ 不能做 | 访问远程仓库或读取用户本地文件内容 |
| ❌ 不能做 | 判断代码正确性或审查代码质量 |
| ❌ 不能做 | 绕过 Git 权限控制或安全策略 |

**适用对象**：需要标准化 Git 操作流程的个人开发者、小型团队协作场景、教学演示环境。


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: braid
name: braid
displayName: 分支追踪 版本管理 供应商代码
description: 追踪Git仓库中供应商分支的变更与同步状态，辅助版本管理。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/braid
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: BranchPilot
agent_created: true
trigger_words: ["braid", "vendor branch", "供应商分支", "分支追踪", "git vendor", "分支同步"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# braid — 供应商分支追踪助手

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 分支识别 | 识别仓库中供应商分支（vendor branch）的名称、来源、基线提交 | 自动判断哪些分支属于"供应商"——需要用户指定或按命名规则推断 |
| 变更追踪 | 对比供应商分支与主分支的差异，列出新增、修改、删除的文件 | 自动合并代码，解决冲突 |
| 同步状态 | 检查供应商分支是否落后于上游（upstream）或本地主分支 | 自动推送或拉取远程仓库内容 |
| 信息整理 | 将分支状态、提交历史、文件差异整理为结构化报告 | 生成补丁文件或执行 `git cherry-pick` |
| 批量处理 | 一次处理多个分支，输出汇总表格 | 处理非 Git 仓库或未初始化的目录 |

### 1.2 适用对象

- **适用**：使用 Git 管理项目、且需要跟踪第三方代码（如插件、主题、子模块）的开发者。
- **不适用**：非 Git 工作流、单分支项目、需要自动合并冲突的场景。

### 1.3 输入与输出

| 项目 | 说明 |
|------|------|
| 输入来源 | 用户提供的 Git 仓库路径、分支名称、URL（远程仓库地址） |
| 输出格式 | Markdown 表格 + 结构化文本，包含分支名、状态、差异文件数、置信度标注 |
| 输出文件 | 默认输出到终端，可指定输出到文件（如 `report.md`） |


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

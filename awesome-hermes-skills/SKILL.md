---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: awesome-hermes-skills
name: awesome-hermes-skills
displayName: 技能集市 检索安装 场景匹配
description: 浏览、检索并安装 Hermes Agent 技能包，覆盖内置、可选与社区来源。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/awesome-hermes-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["awesome hermes skills", "hermes 技能列表", "技能安装", "skill catalog", "技能市场", "技能检索"]

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

# awesome-hermes-skills 技能文档

## 一、能力边界：一页纸速查卡

本技能面向 **Hermes Agent v0.17.0** 用户，用于浏览、检索和安装技能包。它本身不执行任何技能逻辑，而是充当"技能市场入口"。

### 1.1 能做清单

| 序号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 技能目录浏览 | 展示全部可用技能的分类列表（内置/可选/社区） |
| 2 | 关键词检索 | 按名称、描述、标签过滤技能 |
| 3 | 安装指引 | 给出指定技能的安装命令与前置依赖 |
| 4 | 版本自检 | 通过 `--selftest` 检查当前环境兼容性 |
| 5 | 批量操作建议 | 对多技能安装场景给出顺序建议 |

### 1.2 不能做清单

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行技能逻辑 | 本技能只做"导航"，不替代目标技能运行 |
| 2 | 不修改配置文件 | 安装动作需用户手动执行命令 |
| 3 | 不保证兼容性 | 社区技能可能存在依赖缺失，需自行验证 |
| 4 | 不提供离线包 | 所有技能需从官方源或社区源获取 |

### 1.3 适用对象

- **新手用户**：刚接触 Hermes Agent，需要快速了解有哪些技能可用。
- **进阶用户**：需要批量安装或检索特定场景技能。
- **开发者**：需要确认技能与当前版本（v0.17.0）的兼容性。


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: rename
name: rename
displayName: 文件重命名 批量处理 命名规范
description: 提供文件重命名的规范流程、批量处理策略与命名建议，输出可复用的操作方案。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/rename
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨
agent_created: true
trigger_words: ["rename", "重命名", "批量改名", "文件命名", "命名规范"]
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

# 文件重命名 批量处理 命名规范

## 一、能力边界速查卡

### 能做（5项核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 单文件重命名方案 | 根据用户提供的文件信息，给出规范的新文件名建议 |
| 2 | 批量重命名策略 | 针对多文件场景，设计统一的命名规则与序号方案 |
| 3 | 命名规则模板生成 | 输出可复用的命名模板（如 `日期_项目_序号` 格式） |
| 4 | 冲突检测与规避 | 识别重名风险，提供去重策略与占位方案 |
| 5 | 操作步骤清单 | 生成分步执行指南，包含备份、预览、执行、验证环节 |

### 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不直接操作系统文件 | 本技能仅输出方案与步骤，不执行实际文件操作 |
| 2 | 不处理二进制内容 | 不解析文件内部数据，仅基于文件名与元信息工作 |
| 3 | 不保证命名唯一性 | 最终唯一性需用户在执行环境中确认 |
| 4 | 不覆盖特殊权限文件 | 系统保护文件、只读文件需用户自行处理权限 |

### 适用对象

- 需要整理本地文件的个人用户
- 需要批量归档项目文档的团队协作场景
- 需要规范化命名以适配自动化流程的开发人员


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: rename
name: rename
displayName: 文件重命名 批量处理 命名规范
description: 提供文件重命名的规范流程、批量处理策略与命名建议，输出可复用的操作方案。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/rename
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 命名工坊
agent_created: true
trigger_words: ["rename", "重命名", "批量改名", "文件命名", "命名规范", "文件重命名", "批量重命名"]
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

# 文件重命名 Skill 文档

## 一、能力边界速查卡

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 单文件重命名 | 为单个文件提供规范命名建议 | `report_final.docx` → `2024年度财务报告_v2.docx` |
| 批量重命名 | 为多文件生成统一命名方案 | 100张照片 → `2024-10-01_001.jpg` 格式 |
| 命名规范制定 | 根据场景输出命名规则模板 | 项目文档、照片、代码文件等 |
| 重命名风险评估 | 识别重命名可能带来的链接失效、引用断裂等问题 | 被其他文档引用的文件改名后需同步更新引用 |
| 操作步骤生成 | 输出可执行的重命名操作流程（含工具命令） | Windows/macOS/Linux 下的具体操作 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不直接操作文件系统 | 本 Skill 仅输出方案与建议，不执行实际重命名操作 |
| 不处理无权限文件 | 系统保护文件、只读文件、正在使用的文件不在建议范围内 |
| 不提供绝对最优方案 | 命名规范依赖具体业务场景，不存在放之四海皆准的标准 |
| 不保证兼容所有系统 | 不同操作系统对文件名长度、非法字符的限制不同 |

### 1.3 适用对象

- 需要整理个人文件的普通用户
- 需要批量处理项目文档的团队协作人员
- 需要建立文件命名规范的组织/部门
- 需要自动化重命名脚本的开发者


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

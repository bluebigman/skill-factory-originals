---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: openpackage
name: openpackage
displayName: 技能包收纳 批量转换 格式校验
description: 统一收纳、组织、分发技能包与命令，支持批量转换与格式校验。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/openpackage
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林默
agent_created: true
trigger_words: ["openpackage", "技能包管理", "技能组织", "命令编排", "技能分发", "批量转换", "格式校验", "包管理"]
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

# openpackage — 技能包收纳与分发工具

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 收纳 | 将散落的技能文件归入统一目录结构 | 自动识别未标记来源的技能包归属 |
| 组织 | 按标签、类型、版本对技能包分类 | 自动推断技能包之间的依赖关系 |
| 分发 | 将技能包导出为指定格式（JSON/YAML/MD） | 跨网络推送至远程仓库 |
| 转换 | 批量将一种格式转为另一种格式 | 转换过程中自动修复语义错误 |
| 校验 | 检查 frontmatter 必填字段与格式合法性 | 验证技能逻辑的正确性 |
| 命令编排 | 组合多个子命令形成执行链 | 自动生成新的业务逻辑代码 |

### 1.2 适用对象

- **技能包作者**：需要整理、校验、发布前检查
- **团队维护者**：需要统一管理多个技能包版本
- **自动化流水线**：需要批量转换或校验技能包格式

### 1.3 输入输出边界

- 输入：技能包目录路径、文件列表、格式参数
- 输出：校验报告、转换后的文件、目录树清单
- 不处理：技能包内部逻辑、运行时行为、外部服务调用


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

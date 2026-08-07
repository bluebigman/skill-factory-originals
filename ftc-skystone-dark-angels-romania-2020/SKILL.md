---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ftc-skystone-dark-angels-romania-2020
name: ftc-skystone-dark-angels-romania-2020
displayName: FTC机器人 代码结构审查
description: 解析FTC机器人项目代码，提取结构信息并生成审查报告。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ftc-skystone-dark-angels-romania-2020
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: CodeForge Studio
agent_created: true
trigger_words: ["代码审查", "FTC", "SKYSTONE", "机器人代码", "结构解析", "程序分析", "工程检查"]
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

# FTC SKYSTONE 机器人项目代码结构审查 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输出物 |
|--------|------|--------|
| 项目结构解析 | 识别 FTC 机器人项目的目录层级、包结构、类文件分布 | 目录树 + 包结构图 |
| 代码模块识别 | 区分 OpMode、硬件映射、工具类、配置类等模块 | 模块清单表 |
| 依赖关系梳理 | 分析类之间的引用、继承、接口实现关系 | 依赖关系图 |
| 代码规范检查 | 检查命名、注释、代码风格是否符合 FTC 官方规范 | 规范问题清单 |
| 风险点标注 | 识别潜在的空指针、资源泄漏、并发问题 | 风险标注列表 |
| 审查报告生成 | 汇总以上信息，输出结构化 Markdown 审查报告 | 审查报告.md |

### 1.2 不能做什么

- 不执行代码，不进行运行时行为分析
- 不修改源代码，只做静态审查
- 不保证发现所有潜在缺陷（静态分析的固有限制）
- 不评估机器人实际比赛表现
- 不提供硬件配置建议

### 1.3 适用对象

- FTC SKYSTONE（2019-2020）赛季的机器人项目
- 使用 Java 语言编写的 FTC OpMode 代码
- 项目规模在 10~200 个 Java 文件之间
- 需要代码交接、质量评估、赛前检查的团队


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

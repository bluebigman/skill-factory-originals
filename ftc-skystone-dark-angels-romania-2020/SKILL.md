---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ftc-skystone-dark-angels-romania-2020
name: ftc-skystone-dark-angels-romania-2020
displayName: FTC机器人 代码审查 结构解析
description: 解析FTC机器人项目代码，提取结构信息并生成审查报告。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ftc-skystone-dark-angels-romania-2020
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 星尘工坊
agent_created: true
trigger_words: ["代码审查", "FTC", "SKYSTONE", "机器人代码", "结构解析", "代码分析", "审查报告"]
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

# FTC SKYSTONE 代码审查与结构解析 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做（核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| C1 | 代码结构解析 | 解析 FTC SKYSTONE 赛季项目中的 Java/Kotlin 文件，提取类、方法、注解、OpMode 注册信息 |
| C2 | 关键信息识别 | 识别 `@TeleOp`、`@Autonomous` 注解、`LinearOpMode`/`OpMode` 继承关系、硬件映射调用 |
| C3 | 审查报告生成 | 按约定模板输出 Markdown 格式审查报告，包含结构概览、风险点、改进建议 |
| C4 | 置信度标注 | 对无法确认的信息（如外部库依赖、硬件配置）标注 `[需核实:字段]` 占位符 |
| C5 | 批量处理 | 支持多文件/目录输入，批量生成审查结果并汇总 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行代码 | 不编译、不运行、不调试任何代码，仅做静态文本分析 |
| L2 | 不判断硬件兼容性 | 不验证代码与真实机器人硬件的匹配程度 |
| L3 | 不提供性能优化建议 | 不分析算法复杂度或执行效率 |
| L4 | 不处理非文本文件 | 不支持图片、视频、二进制文件输入 |
| L5 | 不保证审查完整性 | 审查结果基于输入内容，不覆盖未提供的文件或依赖 |

### 1.3 适用对象

- FTC 参赛队伍（尤其是 SKYSTONE 赛季）的代码维护者
- 需要快速了解陌生 FTC 项目结构的开发者
- 准备代码评审会议的团队负责人


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

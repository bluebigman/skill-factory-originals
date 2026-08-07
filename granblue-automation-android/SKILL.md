---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: granblue-automation-android
name: granblue-automation-android
displayName: 碧蓝自动化 安卓脚本编排
description: 将用户提供的操作流程转化为安卓端可执行的自动化脚本配置。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/granblue-automation-android
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Studio
agent_created: true
trigger_words: ["granblue automation android", "碧蓝自动化", "安卓脚本编排", "自动化工作流配置", "手游脚本生成"]
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

# 碧蓝自动化 安卓脚本编排 Skill 文档

## 1. 能力边界（一页纸速查卡）

本 Skill 面向 **《碧蓝幻想》手游的安卓端自动化脚本设计场景**，帮助你把用户口述或文档中的操作意图，整理成结构化、可校验的脚本配置草案。

### 1.1 能做（核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| C1 | 操作流程结构化 | 将用户提供的自然语言步骤（如"打开副本→选择难度→开始战斗"）拆解为有序的步骤节点 |
| C2 | 关键参数识别与保留 | 从输入中提取坐标、按钮名称、等待时长、循环次数等关键字段，并原样保留 |
| C3 | 约定格式输出 | 按固定的 JSON 结构输出脚本配置，字段名与层级关系稳定 |
| C4 | 置信度标注 | 对每个步骤节点标注置信度（high / medium / low），低置信度项明确标出 |
| C5 | 批量处理与自定义格式 | 支持一次输入多条流程；支持用户指定输出字段的别名或附加字段 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行实际点击操作 | 本 Skill 仅生成配置文本，不直接驱动安卓设备 |
| L2 | 不校验游戏版本兼容性 | 不判断脚本是否适配当前游戏版本，需用户自行确认 |
| L3 | 不处理图像识别逻辑 | 不生成 OpenCV / 模板匹配等图像识别代码，仅做流程编排 |
| L4 | 不保证脚本成功率 | 不承诺任何执行成功率或稳定性，仅按输入生成结构化草案 |

### 1.3 适用对象

- 需要快速将操作思路落成脚本配置草案的自动化爱好者
- 需要统一脚本配置格式以便团队协作的开发者
- 需要批量整理多条操作流程的测试人员


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

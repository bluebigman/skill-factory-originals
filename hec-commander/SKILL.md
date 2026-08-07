---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: hec-commander
name: hec-commander
displayName: 水文建模 脚本自动化 命令行工具
description: 面向HEC系列软件的AI辅助脚本生成与自动化操作指南。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/hec-commander
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Studio
agent_created: true
trigger_words: ["hec-commander", "HEC-RAS", "HEC-HMS", "水文建模", "脚本自动化", "水动力模拟"]
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

# HEC Commander 技能文档

## 一、能力边界速查卡

本 Skill 面向水利工程师、建模分析师与自动化脚本开发者，用于辅助完成 HEC-RAS（河道水动力分析）与 HEC-HMS（流域水文模拟）的第三方脚本编写与自动化任务编排。

| 维度 | 说明 |
|------|------|
| ✅ 能做 | 解析用户提供的模型文件路径、参数表、模拟场景描述，生成可执行的 Python/命令行脚本框架 |
| ✅ 能做 | 将自然语言描述的建模步骤转换为 HEC 系列软件的 API 调用序列 |
| ✅ 能做 | 识别输入中的关键参数（如糙率、边界流量、降雨序列），并映射到对应 API 参数 |
| ✅ 能做 | 输出带置信度标注的结构化脚本方案，支持批量任务模板生成 |
| ✅ 能做 | 对不确定的模型参数或 API 用法给出 [需核实:字段名] 占位提示 |
| ❌ 不能做 | 直接运行或调试 HEC-RAS/HEC-HMS 软件（需用户本地安装并验证） |
| ❌ 不能做 | 替代专业水文水力计算，不提供数值方法建议 |
| ❌ 不能做 | 访问未公开的 API 接口或绕过软件授权机制 |

**适用对象**：已安装 HEC-RAS 6.x / HEC-HMS 4.x 并具备 Python 基础（或愿意学习）的建模人员。


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

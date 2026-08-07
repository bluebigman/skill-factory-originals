---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ruview
name: ruview
displayName: 空间感知 无线信号 环境监测
description: 将WiFi信号转化为空间感知与存在检测的结构化分析结果。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ruview
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SignalForge Studio
agent_created: true
trigger_words: ["ruview", "WiFi感知", "无线信号分析", "空间监测", "存在检测", "信号处理"]
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

# π RuView — 无线信号空间智能解析 Skill

## 一、能力边界速查卡

本 Skill 面向需要将 WiFi 信号原始数据（如 CSI 振幅、相位、RSSI 序列）转化为结构化空间信息的场景。以下用一页纸说明能做什么、不能做什么。

| 维度 | 说明 |
|------|------|
| **核心输入** | 用户提供的信号数据文件（CSV/JSON/NumPy 数组文本）、数据 URL、或描述信号特征的文本段落 |
| **核心输出** | 结构化 JSON 结果，包含：活动检测、区域占用估计、信号质量指标、置信度评分 |
| **处理范围** | 静态数据分析、趋势识别、异常波动标记、基础活动分类（静止/移动/无人） |
| **明确不做** | 不执行实时信号采集、不连接硬件设备、不进行医学级生命体征诊断、不提供安防决策指令 |

**适用对象**：物联网开发者、环境监测研究者、智能家居爱好者、需要快速验证信号处理思路的技术人员。

**不适用对象**：需要医疗认证的监护设备开发者、需要实时响应的安全系统集成商。


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

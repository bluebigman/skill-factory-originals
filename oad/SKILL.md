---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: oad
name: oad
displayName: 显微成像 自动化流程 脚本编排
description: 面向ZEN Blue显微工作流的Python脚本工具集，助您高效编排自动化任务。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/oad
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Studio
agent_created: true
trigger_words: ["oad", "Open Application Development", "ZEN Blue自动化", "显微脚本", "显微镜工作流"]
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

# oad — 显微成像自动化脚本编排助手

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 序号 | 能力项 | 说明 | 典型场景 |
|------|--------|------|----------|
| 1 | 脚本结构解析 | 分析用户提供的 Python 脚本或伪代码，识别其与 ZEN Blue OAD 框架的关联点 | 用户粘贴一段显微镜控制代码，询问如何改造 |
| 2 | 工作流步骤梳理 | 将用户描述的实验流程拆解为可执行的步骤序列，并映射到 OAD 工具函数 | 多通道采集、时间序列、拼图扫描等 |
| 3 | 参数配置建议 | 根据用户输入的硬件型号与实验目标，给出合理的采集参数范围 | 曝光时间、增益、Z层间距等 |
| 4 | 错误排查辅助 | 针对用户报错信息，定位可能的原因并给出修正方向 | 设备未连接、参数越界、脚本语法错误 |
| 5 | 批量任务编排 | 帮助用户设计循环遍历、条件判断等控制结构，实现多组样本的自动化处理 | 96孔板逐孔采集 |

### 1.2 不能做什么

- 不能直接执行或调试 Python 代码（需用户在 ZEN Blue 环境中自行运行）
- 不能替代 ZEN Blue 官方文档，具体 API 签名以官方发布为准
- 不能生成完整的商业级应用，仅提供思路与片段级代码参考
- 不能处理与显微镜硬件控制无关的通用编程问题

### 1.3 适用对象

- 使用 ZEN Blue 进行显微成像的科研人员
- 希望用脚本替代手动操作的实验室技术员
- 需要批量处理图像数据的分析人员


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

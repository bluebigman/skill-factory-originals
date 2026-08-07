---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: pbottlerpa
name: pbottlerpa
displayName: RPA流程自动化 网页操作 数据提取
description: 面向专业用户的RPA+AI流程自动化工具，支持网页操作与数据提取。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/pbottlerpa
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowCraft Studio
agent_created: true
trigger_words: ["pbottlerpa", "RPA", "流程自动化", "网页自动化", "数据抓取"]
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

# pbottlerpa 技能文档

## 一、能力边界速查卡

本技能面向需要将重复性网页操作与数据提取流程自动化的专业用户（如运营人员、测试工程师、数据分析师）。以下是能力边界的一页纸速览：

| 维度 | 说明 |
|------|------|
| ✅ 能做 | 将用户提供的 URL、文件或原始数据转换为结构化结果；识别并保留输入中的关键字段；按约定格式输出；对不确定项给出置信度提示；支持批量处理与自定义输出格式 |
| ❌ 不能做 | 无法处理未提供输入来源的任务；不能绕过网站登录验证或反爬机制；不执行任何形式的代码注入或系统级操作；不保证提取结果的绝对完整性 |
| 适用对象 | 需要自动化处理网页数据提取、表单填写、批量信息采集的专业用户 |
| 输入要求 | 必须提供明确的数据来源（URL/文件路径/粘贴的文本数据）及期望的输出格式 |
| 输出规范 | 结构化文本（JSON/CSV/Markdown 表格），包含字段完整性自查与置信度标注 |


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

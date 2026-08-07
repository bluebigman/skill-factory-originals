---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ruflo
name: ruflo
displayName: 数据流编排 多智能体协同 批量转换
description: 将任意数据源解析为结构化结果，支持多智能体协同与批量处理。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ruflo
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingFlow Studio
agent_created: true
trigger_words: ["ruflo", "多智能体", "工作流编排", "数据转换", "批量处理", "数据管道", "结构化解析"]
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

# ruflo — 数据流编排与多智能体协同解析 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 典型场景 |
|--------|------|----------|
| 多源数据接入 | 支持 JSON、CSV、XML、纯文本、API 响应等常见格式 | 从多个接口拉取数据后统一处理 |
| 结构化解析 | 将非结构化或半结构化数据转换为字段明确的表格/对象 | 日志转 JSON、PDF 文本提取关键字段 |
| 多智能体编排 | 将任务拆分为多个子任务，分派给不同智能体并行/串行处理 | 合同审查拆分为条款提取、风险标注、摘要生成 |
| 批量处理 | 对大量数据条目执行同一套转换逻辑 | 批量清洗 10 万行用户数据 |
| 结果合并 | 将多个智能体的输出合并为统一结构 | 多模型答案汇总为一份报告 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行代码 | 不负责运行任意代码，只做数据描述与编排 |
| 不保证数据正确性 | 对输入数据的真实性、完整性不做校验 |
| 不处理实时流 | 面向批处理场景，不适用于毫秒级实时流处理 |
| 不提供存储服务 | 不包含数据库或文件存储能力 |
| 不进行模型训练 | 不涉及机器学习模型的训练或微调 |

### 1.3 适用对象

- 需要将多源数据统一为结构化格式的开发/运维人员
- 需要编排多个 AI 智能体完成复杂任务的场景设计者
- 需要批量清洗、转换数据的分析师


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

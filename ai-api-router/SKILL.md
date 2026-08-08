---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ai-api-router
name: ai-api-router
displayName: API路由 中转配置 模型推荐
description: 根据预算、延迟、模型需求，推荐并配置AI API中转服务，生成接入代码。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ai-api-router
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨
agent_created: true
trigger_words: ["ai-api-router", "API中转", "模型推荐", "API配置", "中转服务", "模型路由", "API接入"]
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

# AI API 中转服务配置助手（ai-api-router）

## 一、能力边界速查卡

本 Skill 用于协助开发者或技术决策者，在接入 AI 模型 API 时，根据自身约束条件（预算、延迟、模型能力）选择合适的中转服务，并生成对应的接入代码与配置说明。

### ✅ 能做（核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 需求解析 | 将用户描述的模糊需求（如"便宜点的""快一点的"）转化为结构化参数（价格上限、延迟阈值、模型类型） |
| 2 | 服务推荐 | 基于内置的常见中转服务参数表，匹配出 1-3 个候选方案，并给出对比 |
| 3 | 配置生成 | 生成 OpenAI 兼容格式的 base_url、api_key 配置示例，以及 Python/curl 调用代码 |
| 4 | 成本估算 | 根据用户预估的调用量（tokens/月），估算月度开销，并标注价格波动风险 |
| 5 | 迁移辅助 | 输出从原服务切换到新服务的步骤清单，包括环境变量修改和代码改动点 |

### ❌ 不能做（边界声明）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不提供真实 API Key | 本 Skill 不生成、不存储、不代理任何真实密钥，仅生成配置占位符 |
| 2 | 不保证服务可用性 | 中转服务可能随时变更政策或下线，推荐结果仅基于训练数据，不构成服务可用性承诺 |
| 3 | 不处理支付/充值 | 所有费用相关问题需用户自行与服务商确认 |
| 4 | 不提供法律合规建议 | 涉及数据出境、合规审查等场景，需咨询专业法律人士 |
| 5 | 不比较所有市场服务 | 仅覆盖训练数据中收录的服务商，未收录的不做评价 |

### 适用对象

- 个人开发者：需要快速接入多个模型，但不想逐一注册多家服务商
- 小型团队：有预算控制需求，希望统一管理 API 调用
- 技术负责人：需要评估不同中转方案的性价比，做技术选型


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

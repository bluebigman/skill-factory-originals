---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: gmail-ai-unsub
name: gmail-ai-unsub
displayName: 邮件退订 智能助手 批量处理
description: 解析邮件退订请求，生成结构化处理方案与操作指引。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/gmail-ai-unsub
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Lab
agent_created: true
trigger_words: ["gmail ai unsub", "邮件退订", "退订助手", "unsubscribe", "批量退订"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# Gmail AI 退订助手 — 技能文档

## 一、能力边界速查卡

### 1.1 能做（核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| C1 | 输入解析 | 将用户提供的邮件内容、文件或退订链接 URL 解析为结构化数据 |
| C2 | 关键信息提取 | 识别发件人、退订链接、邮件类型、退订原因等核心字段 |
| C3 | 格式化工单生成 | 按约定模板输出退订处理工单，含字段、操作步骤与风险提示 |
| C4 | 置信度标注 | 对不确定的字段标注 `[需核实:字段名]`，不编造信息 |
| C5 | 批量处理 | 支持多封邮件/多个链接的批量解析与工单生成 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不代发退订请求 | 本技能仅生成处理方案，不实际调用 Gmail API 或发送退订邮件 |
| L2 | 不绕过验证码 | 不处理需要人机验证的退订流程 |
| L3 | 不保证退订成功 | 退订结果取决于邮件服务商策略，本技能不承诺结果 |
| L4 | 不处理敏感数据 | 不解析含密码、银行账号等敏感信息的邮件内容 |

### 1.3 适用对象

- 需要批量清理订阅邮件的个人用户
- 需要规范化退订流程的运营人员
- 需要审计退订操作记录的管理者


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

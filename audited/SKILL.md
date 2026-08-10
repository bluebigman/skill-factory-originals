---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: audited
name: audited
displayName: 模型审计 变更追踪 数据留痕
description: 为Rails模型自动记录属性变更，提供完整的审计日志与操作追溯能力。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: s://.com/bluebigman/skill-factory-originals/tree/main/audited
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林栖
agent_created: true
trigger_words: ["audited", "acts_as_audited", "审计日志", "模型变更记录", "操作追踪", "数据留痕"]
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

# audited — Rails 模型审计日志 Skill 文档

## 一、能力边界速查卡

### 1.1 核心能力清单

| 能力项 | 说明 | 适用场景 |
|--------|------|----------|
| 自动记录变更 | 在模型上启用后，每次 create / update / destroy 自动生成审计记录 | 需要追踪数据变更历史的业务系统 |
| 关联用户追踪 | 记录操作者（当前登录用户）信息 | 多用户协作的后台管理系统 |
| 自定义字段过滤 | 可指定只审计某些字段，或排除某些字段 | 避免记录敏感字段（如密码）或高频无意义字段 |
| 审计记录查询 | 提供便捷的查询，按模型、记录、时间范围检索 | 合规审查、问题排查、操作回溯 |
| 关联对象审计 | 支持对关联对象（has_many 等）的变更进行审计 | 订单明细、子表数据变更追踪 |

### 1.2 能力边界声明

**能做：**

- 为 Rails ActiveRecord 模型添加审计能力
- 记录模型实例的创建、更新、销毁事件
- 保存变更前后的字段值快照
- 关联操作者信息（需配合认证系统）
- 支持自定义审计字段和条件过滤

**不能做：**

- 不能审计未启用 audited 的模型
- 不能自动识别"操作者"——需要显式设置（如 `Audited.current_user`）
- 不能审计数据库层面的直接 SQL 变更（绕过 ActiveRecord 的操作）
- 不能恢复数据——审计日志仅记录变更，不提供回滚功能
- 不能替代数据库事务日志或 binlog

**适用对象：**

- Rails 4.2+ 应用（含 Rails 7 / 8）
- 需要合规审计、操作留痕的业务系统
- 需要排查数据异常变更的运维场景


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: audited
name: audited
displayName: 审计追踪 数据变更 日志记录
description: 为Rails模型自动记录字段变更历史，支持查询与回放。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/audited
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨轩
agent_created: true
trigger_words: ["audited", "acts_as_audited", "审计日志", "变更记录", "模型审计", "数据追踪"]
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

# audited — Rails 模型变更审计 Skill 文档

## 一、能力边界速查卡

本 Skill 面向 Rails 开发者，帮助你在项目中快速接入、配置和使用 `audited` 这个 ORM 扩展，实现模型字段级变更的自动记录与查询。

### 能做（核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 模型接入配置 | 指导在 Gemfile 添加依赖、执行安装迁移、在模型中声明 `audited` 宏 |
| 2 | 自定义审计字段 | 支持指定只追踪某些字段、忽略某些字段、自定义审计关联名称 |
| 3 | 关联对象审计 | 支持对 `has_many` 等关联集合的变更进行审计（需额外配置） |
| 4 | 查询与回放 | 提供按模型、按记录、按时间范围查询审计日志的方法，支持查看某次变更前后值 |
| 5 | 用户归属标记 | 支持在审计记录中自动记录操作者（当前登录用户），需在控制器中设置 `current_user` |

### 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 非 Rails 环境 | 仅适用于 Rails 4.2+ 及 ActiveRecord ORM，不适用于 Sequel、Mongoid 等 |
| 2 | 字段级加密 | 审计日志以明文存储变更值，不提供字段加密能力 |
| 3 | 自动清理策略 | 不内置日志过期清理任务，需自行实现定时清理 |
| 4 | 跨应用审计 | 仅记录本应用内的模型变更，不追踪外部服务或直接数据库操作 |
| 5 | 异步写入 | 默认同步写入审计记录，不提供异步队列集成（可自行扩展） |

### 适用对象

- 需要满足合规审计要求的 Rails 应用
- 需要追踪关键业务数据（订单、合同、用户信息）变更历史的团队
- 需要实现"谁在什么时候改了什么"的运维排查场景


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

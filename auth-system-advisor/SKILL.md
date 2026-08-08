---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: auth-system-advisor
name: auth-system-advisor
displayName: 认证集成 方案顾问 排障手册
description: 提供 authentik 等认证系统的集成方案、配置指南与故障排查支持。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/auth-system-advisor
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge Studio
agent_created: true
trigger_words: ["认证系统集成", "authentik", "身份验证", "SSO", "单点登录", "OIDC", "LDAP", "认证排障"]
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

# 认证系统集成顾问（auth-system-advisor）

## 一、能力边界速查卡

本 Skill 聚焦于**认证与身份管理领域**的集成方案设计、配置指导与问题诊断。以下内容明确界定其能力范围，帮助您快速判断是否适用。

### ✅ 能做（核心能力）

| 编号 | 能力项 | 说明与示例 |
|------|--------|------------|
| 1 | **方案选型建议** | 根据您的应用类型（Web 应用、API 服务、内部工具）、用户规模、部署环境（K8s、Docker、裸机），推荐合适的认证协议（OIDC / SAML / LDAP）与集成路径 |
| 2 | **配置步骤生成** | 针对 authentik 等系统，生成具体的配置步骤，包括：创建 Provider、配置 Application、设置 Flow、绑定 Policy 等操作指引 |
| 3 | **配置参数解析** | 解释关键配置项的含义、推荐值及影响。例如：`SESSION_COOKIE_SAME_SITE`、`AUTHENTIK_DEFAULT_TOKEN_LENGTH` 等 |
| 4 | **常见故障排查** | 针对重定向错误、令牌验证失败、用户同步异常等高频问题，提供诊断思路与解决步骤 |
| 5 | **最佳实践建议** | 提供安全加固建议（如 MFA 策略、会话超时设置）、性能优化建议（如缓存策略）及架构设计建议（如高可用部署） |

### ❌ 不能做（能力边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | **不执行实际配置** | 本 Skill 仅提供文本指导，无法直接操作您的服务器、修改配置文件或执行命令 |
| 2 | **不提供代码托管** | 不提供完整的、可直接部署的应用程序代码，仅提供配置片段或逻辑伪代码 |
| 3 | **不覆盖非认证领域** | 不处理与认证无关的问题，如：业务逻辑 Bug、数据库性能调优、前端样式问题 |
| 4 | **不保证特定版本兼容性** | 认证系统版本迭代频繁，本 Skill 基于主流稳定版本（如 authentik 2024.x）提供建议，不保证与所有历史版本或未来版本完全兼容 |
| 5 | **不替代官方文档** | 当官方文档与建议冲突时，以官方文档为准。本 Skill 旨在提供经验性指导，不构成最终权威依据 |

### 🎯 适用对象

- **开发者**：需要为应用集成 SSO 或 LDAP 认证的开发人员
- **运维工程师**：负责部署和维护认证服务（如 authentik）的运维人员
- **架构师**：需要设计统一身份认证方案的技术架构师
- **技术决策者**：需要评估认证方案选型的技术负责人


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

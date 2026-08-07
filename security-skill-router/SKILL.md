---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: security-skill-router
name: security-skill-router
displayName: 安全任务路由 工具链匹配 流程编排
description: 按安全任务类型自动匹配工具链与技能包，生成操作流程与知识引用。
version: 1.1.4
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/security-skill-router
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["安全审计", "安全分析", "安全测试", "漏洞评估", "渗透测试", "安全巡检", "风险评估", "安全加固"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# 安全任务路由与工具链编排 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 本 Skill 能做什么

| 能力项 | 说明 | 适用场景示例 |
|--------|------|--------------|
| 任务类型识别 | 从用户描述中提取安全任务类型（审计/分析/测试/评估/渗透） | "帮我看看这个网站安不安全" → 识别为安全测试 |
| 工具链推荐 | 根据任务类型和目标环境推荐合适的工具组合 | 对 Web 应用推荐 Burp Suite + OWASP ZAP + sqlmap |
| 流程编排 | 生成分步骤的执行流程，包含命令、参数和预期输出 | 生成从信息收集到漏洞验证的完整操作序列 |
| 知识引用 | 关联相关的安全知识库、CVE 库、OWASP 指南等 | 对发现的漏洞关联 CVE 编号和修复方案 |
| 报告生成 | 按严重程度排序输出发现结果和修复建议 | 生成包含证据、影响分析和修复步骤的报告 |
| 授权校验 | 在流程开始前确认用户是否具备合法授权 | 检查用户是否提供书面授权或测试范围确认 |

### 1.2 本 Skill 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行实际攻击 | 仅提供流程和工具建议，不代替用户执行任何扫描或攻击操作 |
| 不保证发现所有漏洞 | 安全测试存在局限性，无法保证 100% 覆盖所有潜在风险 |
| 不提供法律意见 | 不判断某项测试是否合法，用户需自行确认授权范围 |
| 不替代专业工具 | 不内置扫描器或漏洞库，仅推荐外部工具和资源 |
| 不处理未授权请求 | 对未确认授权的任务将拒绝生成完整流程 |

### 1.3 适用对象

- 安全工程师：需要快速生成标准化的测试流程
- 开发人员：希望在 CI/CD 中集成安全测试步骤
- 安全团队负责人：需要统一团队的工具链和流程规范
- 安全初学者：需要了解安全测试的基本步骤和工具


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

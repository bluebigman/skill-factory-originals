---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: security-skill-router
name: security-skill-router
displayName: 安全任务路由 工具链匹配 流程编排
description: 按安全任务类型自动匹配工具链与技能包，生成操作流程与知识引用。
version: 1.1.5
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/security-skill-router
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: skill-forge-studio
agent_created: true
trigger_words: ["安全审计", "安全分析", "安全测试", "漏洞评估", "渗透测试", "安全巡检", "风险核查"]
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

# 安全任务路由与工具链编排 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|--------|----------|
| 任务分类 | 根据用户输入的安全任务关键词（审计/分析/测试/漏洞/渗透）识别任务类型 | 无法识别模糊表述（如"帮我看看系统"）——需用户补充任务类型 |
| 工具链匹配 | 为常见安全任务推荐工具组合（如 Nmap + Nikto + Burp Suite） | 不保证工具在目标环境可用，不负责工具安装与配置 |
| 流程编排 | 生成分步骤操作流程（信息收集→扫描→验证→报告） | 不替代人工判断，不自动执行任何命令 |
| 知识引用 | 关联常见漏洞库（CVE/OWASP）与最佳实践文档 | 不提供实时漏洞数据，不保证引用时效性 |
| 输出规范 | 生成结构化任务清单、参数建议、风险提示 | 不生成最终安全报告，仅提供执行框架 |

### 1.2 适用对象

- **安全工程师**：需要快速搭建测试方案
- **运维人员**：进行基础安全巡检
- **开发人员**：自查代码与部署环境风险
- **安全学习者**：了解标准测试流程

### 1.3 输入要求

| 输入项 | 必填 | 示例 |
|--------|------|------|
| 任务类型 | ✅ | "渗透测试" |
| 目标范围 | ✅ | "内网 192.168.1.0/24" |
| 约束条件 | ❌ | "仅限周末凌晨执行" |
| 已有工具 | ❌ | "已装 Kali Linux" |


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

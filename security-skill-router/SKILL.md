---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: security-skill-router
name: security-skill-router
displayName: 安全任务路由 审计测试 漏洞评估
description: 按安全任务类型自动匹配工具链与技能包，生成操作流程与知识引用。
version: 1.1.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/security-skill-router
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Lab
agent_created: true
trigger_words: ["安全审计", "安全分析", "安全测试", "漏洞评估", "渗透测试", "风险评估"]
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

# 安全任务路由 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输出物 |
|--------|------|--------|
| 任务分类 | 识别用户输入的安全任务属于审计/分析/测试/评估中的哪一类 | 分类标签 + 置信度 |
| 工具链匹配 | 根据任务类型推荐对应的工具组合与技能包 | 工具链清单（含优先级） |
| 流程编排 | 生成分步骤的操作流程，含前置条件、执行动作、检查点 | 可执行流程步骤 |
| 知识引用 | 关联相关的安全知识库条目、CVE 编号、最佳实践文档 | 引用列表（含链接或编号） |
| 结果汇总 | 将流程输出整理为结构化报告框架 | 报告模板 + 填充指引 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行实际扫描 | 本 Skill 只生成流程与工具链，不直接调用扫描器或测试工具 |
| 不替代专业判断 | 最终安全结论需由持证安全工程师复核 |
| 不保证发现所有漏洞 | 工具链覆盖范围有限，遗漏风险由使用者自行评估 |
| 不提供修复代码 | 仅给出修复方向与参考资源，不生成补丁或代码片段 |
| 不处理未授权目标 | 若用户未提供授权证明，流程中会强制插入合规检查步骤 |

### 1.3 适用对象

- 安全运维工程师：日常巡检、基线核查
- 渗透测试人员：授权范围内的漏洞验证
- 安全合规专员：等保测评、合规审计
- 开发团队：上线前的安全自测
- 安全学习者：理解标准流程与工具组合


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

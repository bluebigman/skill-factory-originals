---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agencycli
name: agencycli
displayName: 智能体编排 团队自治 轻量指挥
description: 用Markdown+YAML定义角色与技能，构建自管理AI代理团队的轻量命令行工具。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agencycli
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["agencycli", "AI代理团队", "多智能体协作", "自管理团队", "agent团队编排"]
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

# agencycli — 自管理AI代理团队编排器

## 一、能力边界速查卡

### 1.1 核心能力清单（能做）

| 序号 | 能力项 | 说明 | 输入示例 | 输出示例 |
|------|--------|------|----------|----------|
| 1 | 角色定义解析 | 从YAML/Markdown中提取角色名称、职责、权限范围 | `roles/researcher.yaml` | 结构化角色对象 |
| 2 | 技能绑定与调度 | 将技能文件映射到对应角色，支持按需加载 | `skills/web_search.md` | 技能调用计划 |
| 3 | 项目结构生成 | 根据项目描述自动生成目录骨架与任务分解 | `project: 市场调研` | 项目树+任务列表 |
| 4 | 代理间消息路由 | 支持角色间任务传递与结果回传 | `@analyst 分析这份数据` | 路由日志+响应内容 |
| 5 | 自检与状态报告 | 运行中输出代理状态、任务进度、错误信息 | `--status` | 状态快照JSON |

### 1.2 明确不做（边界声明）

- **不执行** 任何需要外部API密钥的模型推理（仅做编排调度）
- **不替代** 用户编写实际业务逻辑代码
- **不提供** 图形化界面（纯CLI交互）
- **不保证** 代理团队在无网络环境下运行（依赖远程模型时）
- **不处理** 超过100MB的输入文件（性能限制）

### 1.3 适用对象

- 需要快速搭建多角色AI协作流程的开发者
- 使用Markdown/YAML管理项目配置的团队
- 希望以轻量方式试验多智能体模式的个人用户


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

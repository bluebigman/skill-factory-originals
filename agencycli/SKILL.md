---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agencycli
name: agencycli
displayName: 智能体编排 团队协作 自动化调度
description: 轻量级CLI工具，通过Markdown+YAML定义角色、技能与项目，驱动AI智能体团队自主协作。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agencycli
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["agencycli", "智能体团队", "AI代理编排", "自主协作", "多智能体调度"]
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

# agencycli — 智能体团队编排命令行工具

## 一、能力边界（一页纸速查卡）

### ✅ 能做（5项核心能力）

| 编号 | 能力项 | 说明 | 示例 |
|------|--------|------|------|
| 1 | 角色定义解析 | 从YAML配置中读取智能体角色、职责与权限范围 | `roles/analyst.yaml` 定义数据分析师角色 |
| 2 | 技能注册与调用 | 将Markdown格式的技能文档注册为可执行技能，供智能体调用 | `skills/web-search.md` 注册网络搜索技能 |
| 3 | 项目任务编排 | 根据项目描述自动拆解任务，分配给合适的智能体角色 | 输入项目目标，自动生成任务清单与分配方案 |
| 4 | 执行状态追踪 | 实时监控各智能体执行进度，输出结构化状态报告 | `agencycli status` 查看当前任务执行情况 |
| 5 | 结果汇总输出 | 收集各智能体产出，按约定格式生成最终交付物 | 输出为 `output/` 目录下的结构化文件 |

### ❌ 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行外部API调用 | 工具本身不直接调用第三方API，需通过技能定义接入 |
| 2 | 不处理非结构化输入 | 输入必须为Markdown或YAML格式，其他格式需先转换 |
| 3 | 不提供图形界面 | 纯命令行交互，无GUI或Web界面 |
| 4 | 不保证任务成功率 | 任务执行结果取决于智能体能力与输入质量，工具仅提供编排框架 |
| 5 | 不支持实时人机对话 | 非交互式执行，任务提交后按预设流程运行 |

### 🎯 适用对象

- **开发者**：需要快速搭建多智能体协作流程的工程团队
- **运维人员**：需要自动化处理重复性任务编排的运维团队
- **项目经理**：需要将项目拆解为可并行执行任务的协调者
- **AI研究者**：需要实验多智能体协作模式的研究人员


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: awesome-gamedev-agent-skills
name: awesome-gamedev-agent-skills
displayName: 游戏开发 智能路由 技能编排
description: 为AI编程代理提供游戏开发技能安装与路由加载能力，一次安装，按需调用。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/awesome-gamedev-agent-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["awesome-gamedev-agent-skills", "gamedev skills", "游戏开发技能", "技能路由", "skill router", "游戏开发代理"]
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

# awesome-gamedev-agent-skills 技能文档

## 一、能力边界：一页纸速查卡

本 Skill 是一个**技能路由中枢**，不直接实现具体游戏功能，而是负责将请求分发到合适的子技能。请先确认以下边界，避免误用。

### ✅ 能做（核心能力）

| 能力项 | 说明 | 典型输入 | 输出形态 |
|--------|------|----------|----------|
| 技能路由 | 根据任务描述匹配并加载对应子技能 | "帮我写一个敌人AI脚本" | 加载对应技能并执行 |
| 数据解析 | 将用户提供的文件/URL/文本转换为结构化数据 | 游戏设计文档、配置表 | JSON/表格结构化结果 |
| 信息提取 | 识别并保留输入中的关键实体与参数 | 需求描述、Bug报告 | 关键字段清单 |
| 批量处理 | 支持多文件、多条目的一次性处理 | 多个资源文件路径 | 批量处理结果汇总 |
| 置信度标注 | 对不确定的输出结果给出可信度提示 | 模糊需求、缺失参数 | 置信度百分比标注 |

### ❌ 不能做（明确边界）

| 禁止事项 | 说明 |
|----------|------|
| 不生成游戏引擎代码 | 本Skill只做路由与编排，不直接编写Unity/Unreal/Godot等引擎代码 |
| 不替代具体子技能 | 若未安装对应子技能，路由会失败并提示，不会自行伪造实现 |
| 不处理非游戏领域任务 | 如财务计算、法律文书等与游戏开发无关的请求 |
| 不保证结果可用性 | 输出结果需人工复核，不承担运行正确性担保 |
| 不执行外部命令 | 本Skill仅处理文本与结构化数据，不触发系统级操作 |

### 👥 适用对象

- **AI编程代理**：作为Claude、Cursor等工具的技能加载入口
- **游戏开发工程师**：需要快速调用各类开发子技能
- **技术美术/策划**：需要将设计文档转化为结构化配置


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

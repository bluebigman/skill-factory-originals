---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: rpgmaker-agent-skills
name: rpgmaker-agent-skills
displayName: RPGMaker 工程读写 安全操作
description: 让AI安全读写RPG Maker MV/MZ工程文件，避免损坏项目结构。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/rpgmaker-agent-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: ProjectForge Studio
agent_created: true
trigger_words: ["rpgmaker", "rpg maker", "mv", "mz", "游戏工程", "地图数据", "事件脚本", "数据库", "插件配置"]
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

# RPG Maker 工程安全读写 Skill 文档

## 一、能力边界（一页纸速查卡）

### 能做（5 项核心能力）

| 编号 | 能力项 | 说明 | 适用对象 |
|------|--------|------|----------|
| 1 | 工程结构解析 | 读取 `Game.rpgproject`、`data/` 目录下的 JSON 文件，识别工程类型（MV/MZ）与版本 | 需要了解工程整体结构的开发者 |
| 2 | 地图与事件数据读取 | 解析 `Map001.json`、`CommonEvents.json` 等文件，提取事件页、指令序列、条件分支等结构化信息 | 需要审查或修改游戏逻辑的开发者 |
| 3 | 数据库对象安全修改 | 对 `Actors.json`、`Items.json`、`Skills.json` 等数据库文件进行字段级增删改，保持 JSON 结构完整 | 需要调整角色、物品、技能属性的开发者 |
| 4 | 插件配置校验 | 读取 `js/plugins.js`，校验插件名称、状态、参数格式是否符合 RPG Maker 规范 | 需要排查插件冲突或配置错误的开发者 |
| 5 | 批量操作与格式转换 | 对多个地图或数据库文件执行批量字段替换、批量导出为 CSV/表格格式 | 需要批量调整数值或导出数据做分析的开发者 |

### 不能做（明确拒绝的边界）

| 编号 | 限制项 | 原因 |
|------|--------|------|
| 1 | 不执行游戏内测试或运行游戏 | 本 Skill 仅处理静态文件，不涉及运行时行为 |
| 2 | 不修改二进制资源（图片、音频、字体） | 这些文件不在 JSON 文本范围内，无法安全读写 |
| 3 | 不处理加密/混淆后的工程文件 | 加密后的 JSON 无法解析，需先解密 |
| 4 | 不自动备份或恢复工程 | 备份操作需由使用者自行完成，本 Skill 不触发文件系统级操作 |
| 5 | 不跨版本自动迁移（MV→MZ） | 数据结构差异较大，迁移需人工确认 |

### 适用对象

- 使用 Claude Code、Codex 或 Cursor 等 AI 编程助手，且项目为 RPG Maker MV/MZ 的开发者
- 需要批量调整游戏数值、审查事件逻辑、排查插件配置的独立游戏开发者
- 希望在不破坏工程结构的前提下，让 AI 辅助完成数据修改的团队


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

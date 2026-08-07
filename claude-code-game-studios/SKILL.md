---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: claude-code-game-studios
name: claude-code-game-studios
displayName: 游戏工坊 数据转换 结构输出
description: 将用户提供的游戏相关数据、文件或URL转换为结构化结果，支持批量处理与自定义格式。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/claude-code-game-studios
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨研
agent_created: true
trigger_words: ["claude code game studios", "游戏工坊", "游戏数据转换", "结构化输出", "批量处理", "游戏工作室"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# Claude Code Game Studios — 技能文档

## 一、能力边界速查卡

本技能定位为**通用数据转换与结构化输出工具**，面向游戏开发、游戏运营、游戏数据分析等场景下的数据整理需求。

### ✅ 能做（核心能力）

| 编号 | 能力项 | 说明 | 适用示例 |
|------|--------|------|----------|
| 1 | 数据/文件/URL 转结构化结果 | 将输入内容解析为 JSON、表格、Markdown 等结构化格式 | 将 CSV 玩家数据转为 JSON 对象数组 |
| 2 | 关键信息识别与保留 | 自动提取输入中的核心字段，过滤冗余信息 | 从游戏日志中提取玩家 ID、等级、时间戳 |
| 3 | 按约定格式生成输出 | 支持自定义输出模板，字段顺序、命名可配置 | 按指定字段顺序输出角色属性表 |
| 4 | 置信度标注 | 对不确定的字段值标注置信度，不强行填充 | 对缺失的玩家昵称标注 `[需核实:player_name]` |
| 5 | 批量处理与自定义格式 | 支持多文件/多 URL 批量输入，输出格式可定制 | 一次处理 10 个关卡配置文件并合并输出 |

### ❌ 不能做（边界声明）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不生成游戏内容 | 不创作剧情、关卡设计、数值策划等原创内容 |
| 2 | 不执行代码 | 不运行、调试或执行任何程序代码 |
| 3 | 不访问外部 API | 不主动调用第三方服务获取数据（仅处理用户提供的 URL 内容） |
| 4 | 不保证数据准确性 | 对输入数据的真实性、完整性不负责，仅做格式转换 |
| 5 | 不处理非文本内容 | 不识别图片、音频、视频中的信息（仅处理文本、代码、表格等） |

### 适用对象

- 游戏策划：整理数值配置、关卡参数
- 游戏运营：汇总活动数据、玩家反馈
- 游戏开发：转换配置文件、日志解析
- 数据分析师：清洗游戏数据、生成报表


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

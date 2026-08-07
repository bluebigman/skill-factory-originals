---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ponytail
name: ponytail
displayName: 懒人编程 代码精简 极简实现
description: 让AI代理以最省代码的方式解决问题，输出最小可行实现。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ponytail
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: lazy-dev-studio
agent_created: true
trigger_words: ["ponytail", "懒人编程", "极简实现", "最少代码", "偷懒开发"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 懒人编程（ponytail）Skill 文档

## 一、能力边界速查卡

### 能做（5 项核心能力）

| 编号 | 能力项 | 说明 | 典型场景 |
|------|--------|------|----------|
| 1 | 输入转结构化结果 | 将用户提供的数据、文件内容或 URL 指向的资源，解析为结构化输出 | 从 CSV 提取字段、从网页抓取关键信息 |
| 2 | 关键信息识别与保留 | 自动识别输入中的核心实体、数值、关系，并在输出中完整保留 | 从日志中提取错误码、从合同中提取金额与日期 |
| 3 | 按约定格式输出 | 严格遵循用户指定的输出格式（JSON / Markdown / 纯文本等） | 生成 API 响应体、生成报表 Markdown |
| 4 | 置信度标注 | 对每个输出字段标注置信度（高/中/低），不确定时明确提示 | 从模糊文本中提取信息时标注可信程度 |
| 5 | 批量处理与自定义格式 | 支持多条输入并行处理，支持用户自定义输出模板 | 批量处理 100 条日志、按自定义模板生成周报 |

### 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行代码 | 本 Skill 只负责设计和输出代码方案，不负责运行或调试 |
| 2 | 不保证最优解 | 输出的是"足够省"的方案，不承诺是全局最优实现 |
| 3 | 不处理未明确需求 | 输入需求模糊时，必须先向用户确认，不擅自假设 |
| 4 | 不生成完整项目骨架 | 只输出核心逻辑片段，不生成配置文件、依赖清单等外围内容 |
| 5 | 不替代人工审查 | 输出结果需用户自行审查后再投入使用 |

### 适用对象

- 需要快速原型验证的开发者
- 希望减少样板代码的日常开发场景
- 对代码量有严格约束的嵌入式或前端场景
- 教学演示中需要展示"最小可行实现"的场景

---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

## 二、触发方式

### 触发词

- 主触发词：`ponytail`
- 同义触发词：`懒人编程`、`极简实现`、`最少代码`、`偷懒开发`

### 场景映射表

| 用户说（大白话） | 触发行为 |
|------------------|----------|
| "用 ponytail 帮我处理这份数据" | 进入数据解析模式，提取关键字段并结构化输出 |
| "这个功能用最少代码怎么写？" | 进入极简实现模式，输出最短可行代码方案 |
| "帮我偷个懒，把这段逻辑简化一下" | 进入代码精简模式，对已有代码做瘦身 |
| "用 ponytail 批量处理这些文件" | 进入批量处理模式，逐条解析并汇总输出 |
| "按这个模板输出结果" | 进入自定义格式模式，按用户模板生成输出 |


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: codex-cli-usage-advisor
name: codex-cli-usage-advisor
displayName: Codex CLI 配置排障与订阅选型助手
description: 解决 Codex CLI 配置、截断、订阅等常见问题，提供实用建议。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/codex-cli-usage-advisor
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: TechFlow Studio
agent_created: true
trigger_words: ["codex-cli", "codex cli", "codex-cli-usage-advisor", "codex 配置", "codex 订阅", "codex 截断"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# Codex CLI 配置排障与订阅选型助手

## 一、能力边界速查卡

### 1.1 能做什么

| 编号 | 能力项 | 输入示例 | 输出示例 |
|------|--------|----------|----------|
| C1 | 解析用户提供的配置文件、日志片段或 URL，提取关键参数 | `~/.codex/config.toml` 内容 | 结构化参数清单（含当前值、建议值） |
| C2 | 识别 API 配置中的常见错误（如 Key 缺失、Base URL 错误） | 报错日志片段 | 错误类型 + 修正步骤 |
| C3 | 针对大文本截断问题给出参数调整建议 | `max_tokens` 设置值 | 推荐配置组合（含上下文窗口计算） |
| C4 | 对比不同订阅方案（免费版 / Pro / 企业版）的适用场景 | 用户月调用量估算 | 方案对比表 + 推荐结论 |
| C5 | 生成自定义格式的配置建议报告（JSON / Markdown） | 用户指定输出格式 | 格式化报告 |

### 1.2 不能做什么

- 不能直接修改用户的本地配置文件（仅提供修改建议）
- 不能访问用户的 API 密钥或验证密钥有效性
- 不能替代官方文档作为最终依据（以官方发布为准）
- 不能预测未来价格变动或功能更新
- 不能处理与 Codex CLI 无关的通用编程问题

### 1.3 适用对象

- 初次接触 Codex CLI 的开发者（需要快速上手配置）
- 遇到 API 连接失败、响应截断等问题的使用者
- 需要评估订阅方案的个人开发者或小团队

---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

## 二、触发方式与场景映射

### 2.1 触发词表

| 触发词 | 场景描述 |
|--------|----------|
| `codex-cli` / `codex cli` | 用户直接提及工具名称 |
| `codex 配置` | 涉及配置文件、环境变量设置 |
| `codex 订阅` | 询问付费方案选择 |
| `codex 截断` | 输出内容被截断的问题 |
| `codex 报错` / `codex 错误` | 遇到运行时报错 |
| `codex api` | API 相关配置问题 |

### 2.2 场景映射示例

| 用户原话 | 映射能力 | 处理路径 |
|----------|----------|----------|
| "我的 codex 一直提示 API key 无效" | C2 | 进入标准流程 → 配置诊断分支 |
| "输出到一半就断了，怎么调大？" | C3 | 进入标准流程 → 截断优化分支 |
| "个人用，选哪个套餐划算？" | C4 | 进入标准流程 → 订阅对比分支 |
| "帮我看看这个配置文件有什么问题" | C1 | 进入标准流程 → 配置解析分支 |


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

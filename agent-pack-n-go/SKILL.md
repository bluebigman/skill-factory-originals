---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agent-pack-n-go
name: agent-pack-n-go
displayName: 智能体迁移 配置打包 一键克隆
description: 将OpenClaw智能体配置、记忆与技能打包，迁移至新设备。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agent-pack-n-go
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Ling
agent_created: true
trigger_words: ["agent pack n go", "克隆智能体", "迁移配置", "打包技能", "设备迁移", "备份智能体"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# agent-pack-n-go — 智能体迁移打包指南

## 一、能力边界速查卡

本 Skill 用于协助你将 OpenClaw 智能体的核心资产（配置文件、记忆存储、技能目录）从当前设备迁移至新设备。以下表格明确列出可处理与不可处理的事项。

| 能力维度 | 可处理（✅） | 不可处理（❌） |
| :--- | :--- | :--- |
| **配置迁移** | `~/.openclaw/` 下的 `config.yaml`、`settings.json` 等标准配置文件 | 操作系统级环境变量、系统服务注册表项 |
| **记忆迁移** | 记忆目录下的结构化存储文件（如 `memory/` 文件夹内的 `.md` 或 `.json` 文件） | 存储在外部数据库（如 Redis、PostgreSQL）中的记忆数据 |
| **技能迁移** | `skills/` 目录下的自定义技能文件夹及其 `SKILL.md` 文件 | 依赖特定硬件驱动或未打包的 Python 虚拟环境 |
| **数据打包** | 将上述文件打包为单一压缩归档（`.tar.gz` 或 `.zip`） | 加密密钥、API 令牌等敏感凭据的自动提取与转移 |
| **目标还原** | 在新设备上解包归档至对应目录结构 | 自动安装依赖、自动配置网络代理或防火墙规则 |

**适用对象**：使用 OpenClaw 框架、需要更换工作设备或搭建新环境的个人开发者与团队。

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

当出现以下情况时，可调用本 Skill 的流程：

| 触发词/场景 | 具体含义 | 操作指引 |
| :--- | :--- | :--- |
| `agent pack n go` | 用户明确要求执行打包迁移命令 | 直接进入「四、标准执行流程」 |
| "我要换电脑了，怎么把智能体搬过去？" | 用户表达迁移需求但未使用标准命令 | 引导用户执行 `agent pack n go` 命令 |
| "帮我备份一下现在的智能体" | 用户需要临时备份而非立即迁移 | 按打包流程执行，但跳过目标设备还原步骤 |
| "新机器上怎么恢复我的配置？" | 用户已持有归档文件，需要还原指导 | 直接跳转至「还原步骤」章节 |


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

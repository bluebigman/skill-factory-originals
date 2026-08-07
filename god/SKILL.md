---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: god
name: god
displayName: 进程守护 状态监控 服务巡检
description: 基于God的Ruby进程监控配置与运维辅助工具
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/god
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: ProcessWarden
agent_created: true
trigger_words: ["god", "进程监控", "ruby进程", "进程守护", "服务巡检", "watch_process"]
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

# God 进程监控 Skill 使用指南

## 一、能力边界速查卡

### 本 Skill 能做什么

| 序号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 配置生成 | 根据用户描述的进程特征，生成 God 配置文件（.god 文件） |
| 2 | 命令解析 | 解释 god 命令行工具（`god`、`god --selftest`、`god --version`）的用途与输出 |
| 3 | 状态诊断 | 分析用户提供的 god 日志或状态输出，定位常见问题 |
| 4 | 最佳实践建议 | 提供 watch 配置、内存限制、重启策略等参数建议 |
| 5 | 批量配置模板 | 为多进程场景生成可复用的配置模板 |

### 本 Skill 不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行命令 | 不代替用户在终端运行 god 命令 |
| 2 | 不处理非 Ruby 环境 | 仅针对 God（Ruby 生态）进程监控工具 |
| 3 | 不提供安全绕过 | 不提供绕过系统权限或安全策略的方法 |
| 4 | 不保证监控效果 | 配置生成后需用户自行验证，不承担运行责任 |
| 5 | 不覆盖全部版本差异 | 主要基于 God 0.13.x 版本行为，其他版本需自行核对 |

### 适用对象

- 使用 Ruby 技术栈的运维/开发人员
- 需要守护常驻进程（Sidekiq、Puma、Delayed Job 等）的团队
- 正在评估或已选用 God 作为进程监控方案的工程师


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

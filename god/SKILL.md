---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: god
name: god
displayName: 进程守护 Ruby监控 配置巡检
description: 基于God的Ruby进程监控配置与运维辅助工具
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/god
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 运维工坊
agent_created: true
trigger_words: ["god", "进程监控", "ruby进程", "进程守护", "服务巡检", "--selftest", "--version", "进程看护", "守护进程"]

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

# God 进程监控配置与运维辅助 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 典型场景 |
|--------|------|----------|
| 配置生成 | 生成 God 配置文件（.god 文件） | 新增 Ruby 服务需要纳入监控 |
| 配置校验 | 检查 Godfile 语法与依赖 | 修改配置后上线前检查 |
| 状态巡检 | 读取 God 运行状态、进程列表 | 日常巡检、故障排查 |
| 操作指令 | 生成 start/stop/restart/load/unload 命令 | 手动控制受管进程 |
| 日志分析 | 解析 God 日志中的告警与事件 | 定位进程反复重启原因 |
| 自检辅助 | 解释 --selftest 输出含义 | 环境安装后验证 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不替代 God 本体 | 本 Skill 不包含 God 程序，需自行安装（gem install god） |
| 不执行远程操作 | 仅生成本地命令，不通过 SSH 操作远程主机 |
| 不自动修复 | 发现异常后给出建议，不自动修改系统配置 |
| 不支持非 Ruby 进程 | God 原生面向 Ruby 进程，其他语言需通过 shell 包装 |
| 不处理网络拓扑 | 不涉及负载均衡、服务发现等上层架构 |

### 1.3 适用对象

- 使用 God 管理 Ruby 服务的运维工程师
- 需要快速上手 God 的开发人员
- 负责服务巡检的 SRE 团队成员


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

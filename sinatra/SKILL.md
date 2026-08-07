---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: sinatra
name: sinatra
displayName: Web开发 DSL 路由构建器
description: 基于Sinatra DSL的轻量Web应用路由设计与调试辅助工具。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/sinatra
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["sinatra", "ruby web", "dsl", "路由设计", "轻量web框架", "rack应用"]
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

# Sinatra DSL 路由设计助手

## 一、能力边界速查卡

### 能做什么
| 编号 | 能力项 | 说明 | 适用场景 |
|------|--------|------|----------|
| 1 | 路由结构解析 | 从用户提供的代码片段/描述中提取路由定义 | 审查现有路由、梳理接口清单 |
| 2 | 路由冲突检测 | 识别相同HTTP方法与路径的重复定义 | 排查路由覆盖导致的bug |
| 3 | 参数占位符提取 | 识别 `:param` 与 `*glob` 模式 | 设计RESTful接口时确认参数命名 |
| 4 | 过滤器与辅助方法梳理 | 提取 `before`/`after` 过滤器及 `helpers` 块 | 理解请求生命周期中的横切逻辑 |
| 5 | 配置项核对 | 检查 `set` 指令与环境变量使用 | 部署前确认运行环境配置 |

### 不能做什么
- 不能执行或运行 Ruby/Sinatra 代码
- 不能替代测试框架进行行为验证
- 不能自动修复路由冲突，仅提供修改建议
- 不处理非 Sinatra 框架（如 Rails、Roda）的路由语法

### 适用对象
- 正在阅读或维护 Sinatra 项目的开发者
- 需要快速梳理既有路由结构的代码审查者
- 学习 Sinatra DSL 语法的新手


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

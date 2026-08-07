---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: codexassistant
name: codexassistant
displayName: 代码审计 协议调试 自动化增强
description: 通过CDP协议驱动Codex应用，实现外部数据注入与结果结构化提取。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/codexassistant
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 流云工具坊
agent_created: true
trigger_words: ["codexassistant", "codex助手", "CDP调试", "协议注入", "外部增强"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# CodexAssistant 技能文档

## 一、能力边界速查卡

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 数据输入 | 接受用户提供的文件路径、URL、原始文本 | 不接受二进制大文件（>50MB）直接注入 |
| 协议交互 | 通过 CDP 的 `Runtime.evaluate` 注入数据 | 不修改 Codex 安装目录下的任何文件 |
| 结果处理 | 将 Codex 返回的 JSON/文本转为结构化表格 | 不保证 Codex 内部逻辑的绝对正确性 |
| 批量操作 | 支持同一会话内连续处理多个输入项 | 不支持跨会话状态持久化 |
| 格式输出 | 按用户指定字段结构生成 Markdown/JSON | 不生成图片、音频等非文本格式 |

### 1.2 适用对象

- 需要将外部数据（日志、配置文件、API 响应）注入 Codex 进行二次分析的开发者
- 需要自动化回归测试 Codex 对话行为的 QA 工程师
- 需要将 Codex 输出接入 CI/CD 管道的运维人员


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

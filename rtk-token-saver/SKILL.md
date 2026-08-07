---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: rtk-token-saver
name: rtk-token-saver
displayName: 对话瘦身 上下文压缩 代码精简
description: 压缩代码与对话上下文，降低 LLM Token 消耗，适配主流 AI 编码工具。
version: 1.0.6
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/rtk-token-saver
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["rtk-token-saver", "token压缩", "上下文精简", "代码摘要", "对话压缩", "token瘦身", "上下文裁剪"]
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

# rtk-token-saver：对话瘦身与上下文压缩

## 一、能力边界（一页纸速查卡）

### 能做什么

| 能力项 | 说明 | 适用场景 |
|--------|------|----------|
| 代码块压缩 | 去除注释、空行、冗余括号，保留逻辑结构 | 将大段代码粘贴给 LLM 前预处理 |
| 对话历史精简 | 合并重复轮次、删除寒暄、保留关键决策点 | 长会话续接时压缩历史消息 |
| 上下文摘要生成 | 输出结构化摘要（目标/约束/已做/待办） | 切换任务或新会话开场 |
| 结构化信息提取 | 从对话中抽取参数、路径、版本号等关键字段 | 交接给其他工具或脚本 |

### 不能做什么

- 不能理解代码语义，只做词法级压缩，不保证压缩后代码可运行
- 不能自动判断哪些对话内容"重要"，需要用户指定保留策略
- 不能跨会话持久化存储任何数据，所有处理均在当前会话内完成
- 不能处理二进制文件或非文本格式

### 适用对象

- 使用 AI 编码助手（如 Copilot、Codeium、Cursor 等）的开发者
- 需要将长对话或大段代码发送给 LLM 的普通用户
- 受限于上下文窗口大小，需要手动管理 token 预算的进阶用户


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

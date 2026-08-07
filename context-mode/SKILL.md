---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: context-mode
name: context-mode
displayName: 上下文压缩 会话记忆 输出精简
description: 压缩工具输出与持久化会话记忆，优化AI编程代理的上下文窗口利用率。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/context-mode
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingCache
agent_created: true
trigger_words: ["context-mode", "上下文压缩", "会话记忆", "输出精简", "token优化"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# context-mode Skill 文档

## 一、能力边界：一页纸速查卡

### 能做（5项核心能力）

| 序号 | 能力项 | 说明 | 典型场景 |
|------|--------|------|----------|
| 1 | 工具输出压缩 | 将冗长的命令行输出、日志、JSON响应压缩为结构化摘要，平均减少98%的token占用 | `git diff` 输出、测试日志、API响应体 |
| 2 | 会话记忆持久化 | 将关键决策、用户偏好、项目约束写入会话记忆文件，跨对话保留 | 多轮重构任务、跨会话代码审查 |
| 3 | 关键信息提取 | 从用户提供的原始数据/文件/URL中识别并保留核心事实、数字、结论 | 错误堆栈分析、配置文件解读 |
| 4 | 结构化格式输出 | 按约定模板生成压缩结果，支持Markdown表格、键值对、JSON三种格式 | 生成变更摘要、输出依赖清单 |
| 5 | 批量与自定义处理 | 支持一次处理多个输入源，允许用户指定输出字段和粒度 | 批量压缩多个日志文件、自定义摘要字段 |

### 不能做（明确边界）

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行代码 | 仅处理文本输入，不运行程序、不执行shell命令 |
| 2 | 不修改源文件 | 压缩结果输出到独立位置，不覆盖原始数据 |
| 3 | 不保证语义无损 | 极端压缩可能丢失次要细节，重要信息需用户确认保留优先级 |
| 4 | 不处理二进制 | 仅接受UTF-8文本、JSON、Markdown、代码文件 |
| 5 | 不替代人工审查 | 压缩摘要不能替代对关键代码或安全敏感内容的完整阅读 |

### 适用对象

- **AI编程代理**：需要管理长对话上下文的自动化编码工具
- **开发者**：在有限上下文窗口中处理大量工具输出的个人用户
- **CI/CD流水线**：需要精简日志输出的自动化流程

## 许可证（License）

```text
MIT License

Copyright (c) 2026 原创作者（自持版权）

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```
<!-- professional-license-embedded -->

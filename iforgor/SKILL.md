---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: iforgor
name: iforgor
displayName: 代码语法速查 命令行助手
description: 快速查询代码语法片段，命令行即问即答，提升编码效率。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/iforgor
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SyntaxSage
agent_created: true
trigger_words: ["iforgor", "语法速查", "代码片段", "语法查询", "命令行工具", "code syntax"]
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

# iforgor — 代码语法速查助手

## 一、能力边界（一页纸速查卡）

### ✅ 能做（核心能力）

| 编号 | 能力项 | 说明 | 示例 |
|------|--------|------|------|
| 1 | 语法片段速查 | 根据用户输入的语言与关键词，返回对应语法结构 | `iforgor python list-comprehension` |
| 2 | 多语言覆盖 | 支持主流编程语言（Python/JS/Go/Rust/Java/C++ 等） | `iforgor go goroutine` |
| 3 | 结构化输出 | 以统一格式展示语法、参数、示例与注意事项 | 见「输出规范」 |
| 4 | 自检与版本查询 | 内置自检命令与版本号输出 | `iforgor --selftest` / `--version` |
| 5 | 模糊匹配提示 | 输入不精确时给出候选列表，引导用户确认 | `iforgor py list` → 提示候选 |

### ❌ 不能做（明确边界）

- 不执行代码，不返回运行结果
- 不提供完整教程或系统性教学
- 不解析自然语言长句（仅支持关键词匹配）
- 不联网获取实时文档（基于内置知识库）
- 不保证覆盖所有语言的全部语法（以常见高频为主）

### 🎯 适用对象

- 初级开发者：快速回忆语法写法
- 中级开发者：跨语言切换时查漏补缺
- 面试准备者：快速浏览高频语法点


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

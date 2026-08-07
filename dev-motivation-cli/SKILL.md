---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: dev-motivation-cli
name: dev-motivation-cli
displayName: 开发者激励 命令行输出 数据转换
description: 为开发者提供命令行激励工具的结构化输出与数据转换规范。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/dev-motivation-cli
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["dev motivation cli", "开发者激励", "命令行激励工具", "dev-motivation-cli", "motivation cli", "开发者打气", "终端鼓励语"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# dev-motivation-cli 技能文档

## 一、能力边界速查卡

本技能面向需要将命令行激励工具的输出结果进行规范化处理的开发者、技术写作者或自动化流水线维护者。它不负责生成激励内容本身，只负责定义“如何把激励结果变成结构化数据”。

| 维度 | 说明 |
|------|------|
| 核心能力 | 将命令行工具的输出转换为 Markdown 或 JSON 格式 |
| 输入要求 | 工具的标准输出（stdout）或退出码（exit code） |
| 输出格式 | 严格遵循本技能定义的 Markdown 模板或 JSON Schema |
| 适用场景 | 脚本集成、CI/CD 日志美化、开发者工具文档编写 |
| 不适用场景 | 生成激励文案、分析开发者心理状态、替代原工具运行 |

### 能做与不能做

**能做：**
- 解析命令行工具的标准输出，提取关键字段（如激励语、时间戳、等级）
- 将解析结果映射为 Markdown 表格或 JSON 对象
- 校验输出是否符合预定义的结构规范
- 在信息缺失时生成 `[需核实:字段名]` 占位符

**不能做：**
- 修改或优化激励工具本身的算法
- 保证输出内容对特定人群一定有效
- 处理二进制输出或非文本流
- 自动推断未提供的元数据（如作者身份、工具版本）

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

当你在以下场景中说出触发词，本技能将介入：

| 触发词/短语 | 典型场景 | 期望结果 |
|-------------|----------|----------|
| “dev motivation cli” | 在终端运行工具后，需要格式化输出 | 得到 Markdown 或 JSON 规范 |
| “开发者激励” | 讨论如何展示激励结果 | 获得结构化输出模板 |
| “命令行激励工具” | 编写集成文档或自动化脚本 | 明确数据转换规则 |
| “motivation cli” | 英文环境下查询用法 | 获得英文参数说明 |
| “终端鼓励语” | 需要将输出嵌入到 CI 日志 | 获得 JSON 格式示例 |

**大白话映射：**
- “我想把这个工具的输出存到文件里” → 使用 JSON 输出模式
- “我想在 README 里展示激励效果” → 使用 Markdown 输出模式
- “我想检查输出是否正常” → 使用 `--selftest` 参数


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

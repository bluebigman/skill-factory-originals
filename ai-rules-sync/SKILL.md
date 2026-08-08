---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ai-rules-sync
name: ai-rules-sync
displayName: 规则同步 配置管理 多端协同
description: 同步、管理与分享 AI 规则、技能、命令与子代理配置。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ai-rules-sync
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SyncForge
agent_created: true
trigger_words: ["ai-rules-sync", "同步规则", "管理AI配置", "分享技能", "规则同步", "配置迁移"]
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

# AI 规则同步与配置管理 Skill

## 一、能力边界速查卡

本 Skill 用于帮助用户在不同 AI 编程工具（如 Cursor、Claude Code、Copilot、OpenCode、Trae）之间同步、管理和分享自定义规则、技能、命令与子代理配置。

| 维度 | 说明 |
|------|------|
| **核心功能** | 解析、转换、校验、导出 AI 工具配置文件 |
| **适用对象** | 使用多种 AI 编程助手的开发者、团队配置管理员 |
| **输入类型** | 本地文件路径、目录、URL 指向的配置文件、粘贴的配置文本 |
| **输出类型** | 标准化 JSON 结构、跨工具映射建议、差异报告 |

### 能做（5 项核心能力）

1. **配置解析**：将用户提供的文件、目录或 URL 中的 AI 规则/技能/命令/子代理配置解析为结构化数据。
2. **关键信息提取**：识别并保留配置中的名称、描述、触发条件、执行逻辑、依赖项等关键字段。
3. **格式标准化**：按约定 Schema 生成统一格式的输出，便于跨工具对比与迁移。
4. **置信度标注**：对解析过程中存在不确定或缺失的字段，明确标注 `[需核实:字段名]`，不进行臆测填充。
5. **批量与自定义处理**：支持多文件批量解析，并允许用户指定输出字段子集或自定义映射规则。

### 不能做（明确边界）

- 不执行或运行任何 AI 规则/技能代码，仅做静态文本解析。
- 不自动修改用户原始文件，所有转换结果默认输出到新文件或终端。
- 不保证跨工具配置的 100% 兼容性，仅提供映射建议与差异提示。
- 不处理加密或二进制格式的配置文件。


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

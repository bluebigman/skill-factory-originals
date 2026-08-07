---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: flowpipe
name: flowpipe
displayName: 云脚本编排 工作流自动化 数据管道
description: 面向云脚本编排与工作流自动化场景，提供结构化数据解析、转换与输出能力。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/flowpipe
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["flowpipe", "云脚本", "工作流自动化", "数据管道", "流程编排"]
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

# Flowpipe 技能文档

## 一、能力边界：一页纸速查卡

### 能做（核心能力）

| 编号 | 能力项 | 说明 | 典型输入示例 |
|------|--------|------|--------------|
| 1 | 数据/文件/URL 结构化解析 | 将用户提供的原始数据、文件内容或链接指向的资源，解析为结构化结果 | CSV 文件、JSON 文本、网页 URL |
| 2 | 关键信息识别与保留 | 从输入中提取关键字段，保留上下文关联信息 | 日志中的时间戳、错误码、资源名称 |
| 3 | 约定格式输出 | 按用户指定的文件类型（JSON/YAML/CSV）与字段结构生成结果 | 输出字段：`{source, timestamp, status, detail}` |
| 4 | 置信度标注 | 对解析结果中不确定的字段给出置信度提示，不掩盖不确定性 | `confidence: 0.85` 或 `[需核实:字段名]` |
| 5 | 批量处理与自定义格式 | 支持多文件/多 URL 批量输入，支持自定义输出模板 | 批量处理 10 个日志文件，输出为自定义 JSON 结构 |

### 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行云端部署 | 本技能仅做数据解析与格式转换，不触发任何云端资源创建或修改操作 |
| 2 | 不访问私有网络资源 | 仅处理用户显式提供的 URL 或数据，不主动探测内网地址 |
| 3 | 不保证数据完整性 | 输入数据缺失或损坏时，输出结果会标注缺失，不进行臆测补全 |
| 4 | 不替代专业审计 | 解析结果仅供流程参考，不构成合规性结论 |

### 适用对象

- 需要将散乱日志/导出数据整理为统一格式的运维工程师
- 需要将外部数据接入内部工作流的开发人员
- 需要批量转换数据格式的数据分析人员


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

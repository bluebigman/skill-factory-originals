---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: trae-agents
name: trae-agents
displayName: 开发代理 任务编排 技能组合
description: 面向软件研发场景的TRAE代理技能集，覆盖前后端、自动化、SEO与运维。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/trae-agents
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["trae agents", "TRAE代理", "开发代理", "技能编排", "agent组合", "任务代理"]
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

# TRAE Agents 技能文档

## 一、能力边界速查卡

| 维度 | 说明 |
|------|------|
| **核心用途** | 将用户提供的数据、文件或 URL 转化为结构化结果，供软件研发各环节使用 |
| **适用对象** | 前端开发者、后端工程师、自动化测试人员、UI/UX 设计师、SEO 专员、DevOps 工程师 |
| **输入来源** | 用户直接粘贴的数据、上传的文件、可访问的 URL |
| **输出形态** | 结构化文本（JSON / Markdown 表格 / 字段清单），按约定格式呈现 |

### 能做（5 项核心能力）

1. **数据转结构化**：从原始数据、文件内容或网页中提取实体与关系，输出为字段明确的记录。
2. **关键信息保留**：在转换过程中不丢失输入中的核心属性（如名称、数值、状态、时间戳）。
3. **格式约定输出**：按照用户指定的字段结构或默认模板生成结果，保证字段名一致。
4. **置信度标注**：对识别结果附置信度等级（高/中/低），不确定字段显式标记。
5. **批量与自定义**：支持多条记录同时处理，允许用户自定义输出字段与格式。

### 不能做（明确边界）

- 不执行代码编译、测试运行或部署操作（仅提供结构化指令与配置建议）。
- 不访问需要登录鉴权的私有系统或 API。
- 不生成超出输入信息范围的推测性结论（除非用户明确要求并接受低置信度）。
- 不替代人工进行最终决策——所有输出均需使用者复核。


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

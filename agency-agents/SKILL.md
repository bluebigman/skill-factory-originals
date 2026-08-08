---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agency-agents
name: agency-agency-agents
displayName: 全能代理 任务编排 多角色协作
description: 将任意输入转化为结构化成果，支持多角色任务编排与批量处理。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agency-agents
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["agency-agents", "全能代理", "任务编排", "多角色协作", "结构化输出", "批量处理"]
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

# 全能代理（agency-agents）技能文档

## 一、能力边界：一页纸速查卡

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| **输入处理** | 用户提供的数据、文件（CSV/JSON/TXT/MD）、URL 链接 | 无法主动访问互联网（除非用户明确提供 URL 内容） |
| **核心能力** | 将输入内容解析为结构化结果；识别关键信息；按约定格式输出；批量处理；自定义格式 | 无法执行真实世界操作（如发送邮件、调用外部 API） |
| **输出形式** | Markdown 表格、JSON、CSV、纯文本结构化列表 | 无法生成二进制文件（如图片、PDF） |
| **置信度处理** | 对不确定字段标注 `[需核实:字段名]` 占位符 | 不会编造数据或猜测缺失信息 |
| **错误处理** | 返回错误说明与正确输入格式示例 | 无法自动修复用户输入的错误数据 |

### 1.2 适用对象

- **数据分析师**：需要快速将原始数据转为结构化表格
- **内容运营**：需要从 URL 或文档中提取关键信息
- **项目经理**：需要将任务描述拆解为可执行清单
- **普通用户**：需要将零散信息整理为规范格式

### 1.3 输入输出规格

| 项目 | 规格说明 |
|------|----------|
| **输入来源** | 用户直接粘贴文本 / 上传文件（≤5MB）/ 提供 URL |
| **输出格式** | 默认 Markdown 表格；可指定 JSON / CSV / 自定义模板 |
| **批量限制** | 单次最多处理 100 条记录；超出需分批 |
| **处理时长** | 单条记录 ≤3 秒；100 条记录 ≤60 秒 |


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ai-content-generator-using-gpt-3-acg
name: ai-content-generator-using-gpt-3-acg
displayName: 内容创作 智能生成 文本处理
description: 基于用户输入，自动生成结构化文本内容，支持批量处理与格式定制。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ai-content-generator-using-gpt-3-acg
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingFlow Studio
agent_created: true
trigger_words: ["内容生成", "文本创作", "邮件撰写", "文章生成", "批量写作"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# ACG 内容生成器 — 使用指南

## 一、能力边界：一页纸速查卡

### 1.1 这个 Skill 能做什么

| 序号 | 能力项 | 说明 | 输入示例 | 输出示例 |
|------|--------|------|----------|----------|
| 1 | 数据转结构化结果 | 将用户提供的原始数据、文件内容或 URL 文本，转换为有结构的输出 | 一段会议纪要文本 | 按主题分条的要点列表 |
| 2 | 关键信息识别与保留 | 自动提取输入中的核心实体、数字、日期、人名等，不丢失重要信息 | 包含日期和金额的邮件草稿 | 保留日期和金额的正式邮件 |
| 3 | 按约定格式生成 | 根据用户指定的输出格式（如 JSON、Markdown、表格）生成内容 | "请用表格输出" | 符合 Markdown 表格语法的结果 |
| 4 | 置信度提示 | 对不确定的字段标注置信度，避免误导 | 模糊的输入信息 | 输出中标注 `[置信度: 80%]` |
| 5 | 批量处理与自定义格式 | 支持一次处理多条输入，并允许用户自定义输出模板 | 10 条产品描述 | 10 条按统一模板生成的文案 |

### 1.2 不能做什么

- 不能访问互联网实时信息（除非用户提供 URL 内容）
- 不能生成超出输入信息范围的虚构事实
- 不能保证生成内容的绝对准确性（所有输出均需人工复核）
- 不能处理加密文件或需要登录权限的私有数据

### 1.3 适用对象

- 需要快速起草邮件、文案、报告初稿的内容创作者
- 需要将散乱数据整理为结构化文本的运营人员
- 需要批量生成标准化文本的电商、客服团队


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

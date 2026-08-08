---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: 1
name: 1
displayName: 条款解析 合规审查 风险标注
description: 解析用户提供的条款文本，提取关键义务与风险点，输出结构化审查报告。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/1
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["条款解析", "协议审查", "合规检查", "风险标注", "合同分析", "条款拆解", "义务提取"]
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

# 条款解析与合规审查 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 核心能力清单

| 序号 | 能力项 | 说明 | 适用场景 |
|------|--------|------|----------|
| 1 | 条款结构化拆解 | 将长文本按逻辑单元切分为独立条款，提取编号、标题、正文 | 用户提供协议全文、服务条款、隐私政策等 |
| 2 | 关键义务识别 | 标记涉及用户/平台责任、付款义务、数据处理的句子 | 需要快速定位责任归属时 |
| 3 | 风险点标注 | 对存在歧义、单方权利过大、赔偿上限等条款进行风险提示 | 签约前审查、合规评估 |
| 4 | 结构化报告输出 | 生成 Markdown 或 JSON 格式的审查结果，含条款编号、原文摘录、解析结论 | 需要将结果导入其他工具或存档 |
| 5 | 置信度分级标注 | 对每项解析结果标注高/中/低置信度，低置信度项给出原因 | 文本存在模糊表述或缺失上下文时 |

### 1.2 能力边界说明

**能做：**
- 处理用户直接粘贴的文本内容（≤ 50,000 字符）
- 处理用户提供的 .txt / .md 文件（≤ 2MB）
- 处理公开可访问的 URL 指向的纯文本内容
- 对英文、中文条款进行解析（混合语言亦可）
- 输出 Markdown 表格或 JSON 结构化数据

**不能做：**
- 不提供法律意见或具有法律效力的结论
- 不处理扫描件、图片中的文字（OCR 不在本 Skill 范围内）
- 不处理加密文件或需要登录才能访问的 URL
- 不保证识别出所有潜在风险点（受限于文本完整性和上下文）
- 不替代专业律师或合规顾问的审核

### 1.3 适用对象

- 需要快速了解一份协议核心内容的产品经理、运营人员
- 需要初步筛查条款风险的法务助理、合规专员
- 需要将条款结构化以便后续处理的技术人员


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

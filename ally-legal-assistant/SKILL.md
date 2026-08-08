---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ally-legal-assistant
name: ally-legal-assistant
displayName: 合同智审助手
description: 面向法律与商务场景的合同条款解析、风险提示与结构化输出工具。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ally-legal-assistant
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge Studio
agent_created: true
trigger_words: ["合同审查", "法律风险", "条款比对", "合同分析", "法务助手"]
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

# Ally 合同智审助手 — Skill 文档

## 一、能力边界：一页纸速查卡

本 Skill 面向**法务人员、商务经理、合同管理员**，用于对合同文本进行结构化解析、风险点提示与关键条款提取。它不是一个法律意见生成器，也不替代专业律师的最终判断。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入 | 合同文本（粘贴/上传）、合同文件 URL、批量合同目录 | 扫描件 OCR（需先转文字）、非中文/英文合同（需先翻译） |
| 处理 | 条款分类、风险关键词识别、金额/日期/主体提取、条款缺失检测 | 判断合同合法性、给出诉讼策略、预测判决结果 |
| 输出 | 结构化 JSON、风险清单、条款比对表、摘要报告 | 生成完整合同范本、自动修改合同原文 |
| 交互 | 单份分析、批量处理、自定义输出字段 | 实时对话式追问（需配合主程序） |

**适用对象**：需要快速浏览合同要点、识别明显风险信号、整理条款对比表的日常办公场景。**不适用对象**：重大并购、跨境交易、诉讼材料等需要执业律师深度介入的场景。


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

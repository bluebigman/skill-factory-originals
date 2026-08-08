---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ailaw1
name: ailaw1
displayName: 合同智审 多维度法律风险扫描
description: 多维度合同法律风险智能扫描与结构化审查工具。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ailaw1
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LegalForge Studio
agent_created: true
trigger_words: ["ailaw1", "合同审查", "法律风险", "条款分析", "合同体检", "法律审阅"]
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

# 合同智审 · 多维度法律风险扫描

## 一、能力边界：一页纸速查卡

本 Skill 面向需要快速评估合同文本风险的非专职法务人员（如产品经理、采购专员、初创团队负责人），提供结构化的法律风险初筛服务。它不替代执业律师的正式法律意见。

### 能做（核心能力清单）

| 序号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 多源输入解析 | 接受用户粘贴的合同文本、上传的 `.txt` / `.md` / `.pdf`（文本型）文件，或指向公开可访问的合同文本 URL |
| 2 | 关键条款识别 | 自动定位并提取合同中的标的、价款、履行期限、违约责任、争议解决、保密、知识产权等核心条款 |
| 3 | 多维度风险扫描 | 从**权利义务对等性**、**合规性**、**可执行性**、**商业合理性**四个维度输出风险提示 |
| 4 | 结构化结果输出 | 按固定字段结构生成 Markdown 审查报告，包含风险等级、条款原文摘录、风险说明与修改建议 |
| 5 | 置信度标注与批量处理 | 对每项风险判断给出置信度（高/中/低）；支持一次提交多份合同（以分隔符区分）并逐份输出报告 |

### 不能做（明确边界）

- 不提供最终法律意见或签约决策建议
- 不识别扫描版 PDF（非文本型）中的图片内容
- 不评估合同涉及的特定行业监管细则（如金融、医疗行业的专项合规）
- 不进行跨合同关联分析（如多份合同之间的冲突检测）
- 不保证覆盖所有潜在法律风险点

### 适用对象

| 适用场景 | 不适用场景 |
|----------|------------|
| 合同签署前的快速自查 | 诉讼策略制定 |
| 供应商/客户合同条款对比 | 并购尽职调查 |
| 内部合同模板的定期体检 | 跨国合同的多法域适用分析 |
| 非标准条款的初步风险识别 | 需要律师签字的正式法律意见书 |


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

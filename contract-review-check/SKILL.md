---
slug: contract-review-check
name: contract-review-check
displayName: 合同审查 风险清单 条款核查
description: 对合同文本进行风险点审查，输出违约、付款、保密、知产归属的核查意见清单。
version: 2.0.4
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/contract-review-check
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Lab
agent_created: true
trigger_words: ["contract-review-check", "合同审查", "风险清单", "条款核查", "合同体检"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# 合同审查·风险清单核查器

## 一、能力边界（速查卡）

本 Skill 用于对合同文本进行结构化风险扫描，输出可供人工复核的审查意见清单。**不替代律师意见，不构成法律建议**。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 审查范围 | 违约责任、付款条款、保密条款、知识产权归属 | 税务筹划、劳动法合规、跨境法律适用、诉讼策略 |
| 输入要求 | 清晰可读的合同文本（纯文本/OCR结果） | 扫描图片（无法OCR）、手写稿、口语化描述 |
| 输出形式 | 分条列出的风险点清单（含条款位置、风险等级、修改建议） | 生成完整合同范本、出具法律意见书 |
| 审查深度 | 基于规则的模式匹配 + 常识性逻辑校验 | 结合判例法、地方性法规的深度法理分析 |

**适用对象**：中小企业主、法务助理、采购/销售岗位人员、初创团队在签署非标准合同前的自查场景。


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

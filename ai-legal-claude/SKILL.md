---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ai-legal-claude
name: ai-legal-claude
displayName: 合同审查与法律风险分析
description: 面向法律专业人士的合同审查、风险分析与合规审计辅助工具。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ai-legal-claude
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LegalForge Studio
agent_created: true
trigger_words: ["合同审查", "法律风险", "NDA生成", "合规审计", "条款比对", "合同分析", "法律文书"]
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

# AI 法律助手（ai-legal-claude）

## 一、能力边界速查卡

本 Skill 面向法律顾问、企业法务、合同管理员及需要处理法律文书的专业人士，提供合同审查、风险分析、NDA 生成与合规审计的辅助支持。

### 能做（核心能力）

| 编号 | 能力项 | 输入要求 | 输出产物 |
|------|--------|----------|----------|
| 1 | 合同条款审查 | 合同文本（PDF/Word/纯文本/URL） | 结构化审查报告（含风险等级） |
| 2 | 法律风险识别 | 合同文本或条款片段 | 风险清单（按严重程度排序） |
| 3 | NDA 模板生成 | 双方主体信息、保密范围、期限 | 可编辑的 NDA 文本 |
| 4 | 合规性初筛 | 合同文本 + 适用法规（可选） | 合规对照表 |
| 5 | 条款比对分析 | 两份或多份合同文本 | 差异对照表 |

### 不能做（明确边界）

- 不提供最终法律意见或替代执业律师的判断
- 不保证审查结果的全面性或绝对准确性
- 不处理涉及诉讼策略、法庭文书起草等诉讼业务
- 不识别扫描件中的手写批注或非标准排版内容
- 不自动执行法律效力评估（如合同是否成立、是否可强制执行）

### 适用对象

- 企业法务团队：合同入库前的初步筛查
- 独立律师：批量合同的快速预审
- 创业公司：NDA 快速生成与基础合规自查
- 法务外包服务商：多客户合同的标准化处理


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

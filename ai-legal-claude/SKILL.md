---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ai-legal-claude
name: ai-legal-claude
displayName: 合同智审 法律风险 条款比对
description: 面向法律场景的合同审查、风险识别、文书生成与合规辅助工具。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ai-legal-claude
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LegalFlow Studio
agent_created: true
trigger_words: ["合同审查", "风险分析", "NDA生成", "合规审计", "条款比对", "法律文书", "合同体检"]
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

# 合同智审 · 法律风险 · 条款比对（SKILL.md）

## 一、能力边界：一页纸速查卡

### 1.1 本 Skill 能做什么

| 序号 | 能力项 | 输入要求 | 输出产物 |
|------|--------|----------|----------|
| 1 | 合同文本结构化解析 | 合同全文（文本/PDF/URL） | 结构化条款清单（JSON/Markdown） |
| 2 | 关键风险点识别 | 合同全文 + 可选风险偏好 | 风险清单（按严重度分级） |
| 3 | NDA/保密协议生成 | 双方主体信息 + 保密期限 | 可编辑的 NDA 文本 |
| 4 | 合规缺口审计 | 合同全文 + 适用法规清单 | 合规差距报告 |
| 5 | 条款比对与差异标注 | 两份或多份合同文本 | 逐条差异对照表 |

### 1.2 本 Skill 不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不提供法律意见 | 输出仅作参考，不构成正式法律建议 |
| 2 | 不替代执业律师 | 重大交易或争议场景须由持证律师复核 |
| 3 | 不保证条款完整性 | 未识别出的风险不代表不存在 |
| 4 | 不执行合同签署 | 不涉及电子签名或公证流程 |
| 5 | 不处理非文本格式 | 扫描件需先经 OCR 转为可读文本 |

### 1.3 适用对象

- 企业法务人员：日常合同初审、风险筛查
- 创业者/中小企业主：NDA 起草、基础合同体检
- 自由职业者：服务协议、保密条款快速核对
- 法律专业学生：条款结构学习、案例比对练习


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

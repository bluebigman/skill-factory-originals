---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: healthcare-agents
name: healthcare-agents
displayName: 医疗行政 智能体协作 流程自动化
description: 面向美国医疗行政场景的51个专科AI智能体便携工具包。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/healthcare-agents
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: AgentForge Studio
agent_created: true
trigger_words: ["healthcare agents", "医疗行政智能体", "医疗流程自动化", "healthcare admin agents", "医疗行政工作流"]
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

# healthcare-agents — 医疗行政智能体协作工具包

## 一、能力边界速查卡

### 1.1 本工具包能做什么

| 序号 | 核心能力 | 说明 | 适用场景举例 |
|------|----------|------|--------------|
| 1 | 数据/文件/URL 结构化转换 | 将非结构化输入（PDF、邮件、网页链接）解析为结构化字段 | 从患者邮件中提取预约信息、从保险单据中抽取理赔字段 |
| 2 | 关键信息识别与保留 | 自动识别姓名、日期、金额、代码等关键实体，保留上下文 | 识别索赔表单中的 CPT 代码、ICD-10 诊断码 |
| 3 | 约定格式输出 | 按用户指定的 JSON/CSV/表格模板生成结果 | 生成符合 EHR 系统导入规范的 CSV 文件 |
| 4 | 置信度标注 | 对每个输出字段标注可信程度（高/中/低） | 手写传真件识别结果标注低置信度 |
| 5 | 批量处理与自定义格式 | 支持多文件批量处理，可自定义输出模板 | 一次性处理 50 份理赔申请，输出自定义汇总表 |

### 1.2 本工具包不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不提供临床诊断建议 | 不替代医生判断，不输出治疗方案 |
| 2 | 不保证合规性 | 不替代 HIPAA 合规审查，不提供法律意见 |
| 3 | 不执行支付操作 | 不发起保险支付、不处理资金转账 |
| 4 | 不连接外部系统 | 不直接对接 EHR/PM 系统，需人工导入导出 |
| 5 | 不处理非文本内容 | 不识别医学影像（X光、MRI 等） |

### 1.3 适用对象

- 医疗行政人员（前台、病历管理员、保险理赔专员）
- 医疗机构的运营支持团队
- 医疗信息化系统集成商（作为预处理工具）
- 医疗咨询与审计人员


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

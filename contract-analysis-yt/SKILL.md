---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: contract-analysis-yt
name: contract-analysis-yt
displayName: 合同审查 风险识别 条款解析
description: 解析合同文本，识别风险点与合规缺口，输出结构化审查报告。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/contract-analysis-yt
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: skill-forge-studio
agent_created: true
trigger_words: ["合同审查", "合同分析", "条款比对", "风险识别", "合规检查", "contract-analysis-yt"]
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

# 合同审查与风险识别 Skill 文档

## 一、能力边界：一页纸速查卡

### 能做（核心能力清单）

| 序号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| 1 | 合同文本解析 | 从用户提供的文件（PDF/Word/TXT）、URL 或直接粘贴的文本中提取合同主体、标的、金额、期限、违约责任等关键要素 | 用户上传一份采购合同 PDF |
| 2 | 风险点识别 | 识别合同中常见的法律风险，如付款条件苛刻、违约责任不对等、知识产权归属模糊、保密义务缺失等 | 合同中出现"买方单方解除权"条款 |
| 3 | 合规性初检 | 对照常见法规要求（如《民法典》合同编、劳动法、数据安全法等）检查合同条款的合规性 | 劳动合同中缺少社保缴纳条款 |
| 4 | 结构化报告输出 | 按约定字段结构生成审查报告，包含风险等级、条款原文摘录、修改建议 | 输出 Markdown 或 JSON 格式报告 |
| 5 | 批量处理与自定义格式 | 支持一次提交多份合同，或按用户指定的字段模板输出结果 | 用户要求按"风险等级+条款编号+建议"三列输出 |

### 不能做（明确边界）

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不提供正式法律意见 | 本 Skill 输出仅为辅助参考，不替代执业律师的法律意见书 |
| 2 | 不保证识别全部风险 | 合同文本的复杂性和歧义性可能导致遗漏，输出结果需人工复核 |
| 3 | 不处理非合同类文档 | 如发票、收据、内部备忘录等非合同性质文件不在处理范围内 |
| 4 | 不执行合同签署或管理 | 本 Skill 仅做分析，不涉及电子签名、合同归档等操作 |
| 5 | 不进行跨语言翻译 | 非中文合同需先由用户自行翻译或说明，本 Skill 不承担翻译功能 |

### 适用对象

- 企业法务人员：合同初审、风险排查
- 商务人员：签约前快速了解合同要点
- 初创团队：无专职法务时的合同自检
- 个人用户：劳动合同、租赁合同等日常合同审查


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

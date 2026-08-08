---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ally-legal-assistant
name: ally-legal-assistant
displayName: 合同智审助手
description: 面向合同文本的智能审查与风险标注工具，支持条款比对与实时问答。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ally-legal-assistant
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingWorks
agent_created: true
trigger_words: ["合同审查", "条款比对", "法律风险", "合同分析", "审阅合同"]
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

# Ally 合同智审助手 — 技能文档

## 一、能力边界（一页纸速查卡）

本 Skill 面向法律合同文本的自动化审查场景，帮助使用者快速定位风险条款、提取关键信息并生成结构化审查报告。

### 1.1 能做清单

| 编号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| C1 | 合同文本解析 | 从用户粘贴的文本、上传的 .txt/.docx 文件或公开 URL 中提取合同正文 | 粘贴 5000 字采购合同文本 |
| C2 | 关键条款识别 | 自动定位付款、违约、保密、管辖等 12 类常见条款 | 合同中出现"违约金"段落 |
| C3 | 风险等级标注 | 对识别出的条款给出 高/中/低 三档风险提示 | 付款周期超过 90 天 → 高风险 |
| C4 | 条款比对 | 将用户提供的两版合同进行差异对比，输出差异清单 | 提供 V1 与 V2 两份合同 |
| C5 | 结构化报告生成 | 按约定模板输出 Markdown 或 JSON 格式审查报告 | 请求输出 JSON 格式 |

### 1.2 不能做清单

| 编号 | 限制项 | 说明 |
|------|--------|------|
| X1 | 不提供法律意见 | 本工具输出仅为信息整理与提示，不构成正式法律建议 |
| X2 | 不处理扫描件 | 暂不支持 OCR 识别，仅接受可复制文本 |
| X3 | 不保证条款完整性 | 若原文存在缺页或遮挡，识别结果可能不完整 |
| X4 | 不执行自动签署 | 不提供电子签名或合同签署功能 |
| X5 | 不替代人工复核 | 所有审查结果需经专业人员复核后方可采信 |

### 1.3 适用对象

- 企业法务人员：日常合同初审与风险筛查
- 商务管理人员：采购、销售合同的关键条款速览
- 律师助理：合同文本的初步整理与比对
- 个人用户：租赁、劳务等常见合同的快速自查


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

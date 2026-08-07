---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ailaw1
name: ailaw1
displayName: 合同智审 法律风险 条款比对
description: 多维度智能合同审查工具，辅助识别法律风险与条款缺失。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ailaw1
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LegalForge Studio
agent_created: true
trigger_words: ["合同审查", "合同分析", "法律风险", "条款比对", "合同体检", "审合同"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# 合同智审 · 多维度法律风险分析 Skill 文档

## 一、能力边界速查卡（一页纸）

### 1.1 能做（核心能力清单）

| 序号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| C1 | 多源数据接入 | 支持用户直接粘贴文本、上传文件（.txt/.docx/.pdf）、提供 URL 链接 | 粘贴合同正文、上传 PDF 扫描件、给出在线合同链接 |
| C2 | 关键信息抽取 | 自动识别合同主体、标的额、期限、违约责任、争议解决条款等核心要素 | 从 30 页合同中提取签约方名称与付款节点 |
| C3 | 多维度风险扫描 | 从合规性、商业合理性、文本严谨性、程序完备性四个维度给出审查意见 | 识别"违约金比例畸高"或"缺少保密条款" |
| C4 | 结构化结果输出 | 按统一字段模板输出审查报告，支持 Markdown / JSON 两种格式 | 生成含风险等级、条款原文、修改建议的报告 |
| C5 | 置信度标注与复核 | 对每项审查结论标注置信度（高/中/低），低置信度项自动标记待核实 | 对模糊表述给出 `[需核实:签约主体资质]` 占位 |

### 1.2 不能做（明确边界）

| 序号 | 限制项 | 说明 |
|------|--------|------|
| N1 | 不提供正式法律意见 | 本工具输出仅为辅助参考，不替代执业律师出具的法律意见书 |
| N2 | 不保证审查完整性 | 受限于输入文本质量与模型能力，可能存在遗漏风险点 |
| N3 | 不处理非文本内容 | 图片中的合同内容需先经 OCR 转文本后方可分析 |
| N4 | 不执行合同修改 | 仅提供修改建议，不直接改动用户提供的原始文件 |
| N5 | 不存储用户数据 | 会话结束后不保留任何合同内容，请勿输入涉密信息 |

### 1.3 适用对象

- **适用**：企业法务、合同管理员、创业者、需要快速了解合同风险点的非法律专业人士
- **不适用**：需要出具具有法律效力的正式审查意见书的场景、涉及国家秘密或商业秘密的合同


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

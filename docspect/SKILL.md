---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: docspect
name: docspect
displayName: 合同审查 条款比对 风险提示
description: 面向合同文本的规范化审阅与风险标注，输出结构化摘要与提示清单。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/docspect
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: lin_analyzer
agent_created: true
trigger_words: ["合同审查", "合同分析", "条款审阅", "风险提示", "合同摘要", "合同体检", "条款比对"]
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

# docspect — 合同文本审阅与风险标注 Skill

## 1. 能力边界（一页纸速查卡）

### 1.1 能做什么

| 编号 | 能力项 | 说明 | 输出物 |
|------|--------|------|--------|
| C1 | 合同结构解析 | 自动识别合同标题、当事人、鉴于条款、定义条款、正文条款、签署页 | 结构树 |
| C2 | 条款分类标注 | 将条款归入付款、交付、违约、保密、知识产权、管辖等类别 | 分类清单 |
| C3 | 风险点识别 | 对模糊表述、缺失要素、失衡权利义务进行标记 | 风险提示列表 |
| C4 | 摘要生成 | 提取合同核心交易结构、金额、期限、关键义务 | 一页纸摘要 |
| C5 | 条款比对 | 支持两份合同逐条对照，输出差异矩阵 | 差异对照表 |

### 1.2 不能做什么

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不提供法律意见 | 本 Skill 仅做文本层面的结构化分析，不构成法律建议 |
| L2 | 不判断合同效力 | 不评估合同是否成立、是否有效、是否可撤销 |
| L3 | 不替代专业审核 | 涉及重大权益的合同，仍需执业律师审核 |
| L4 | 不处理非文本输入 | 仅接受纯文本或可提取文本的文件（PDF 需先转文本） |
| L5 | 不保证条款完整性 | 扫描件、手写批注、图片型 PDF 可能漏检 |

### 1.3 适用对象

- 合同文本（中文为主，中英混排可处理）
- 文本长度：500 字至 50,000 字
- 文件格式：.txt / .md / 可复制文本的 PDF / Word 粘贴文本


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

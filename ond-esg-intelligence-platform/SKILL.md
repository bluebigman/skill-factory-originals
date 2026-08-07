---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ond-esg-intelligence-platform
name: ond-esg-intelligence-platform
displayName: ESG数据洞察 智能解析 报告生成
description: 将ESG数据源解析为结构化结果，支持批量处理与置信度标注。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ond-esg-intelligence-platform
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataCraft Studio
agent_created: true
trigger_words: ["ESG数据解析", "数据可视化", "结构化输出", "批量处理", "置信度标注", "esg-intelligence"]
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

# Ond ESG 智能解析平台 Skill 文档

## 一、能力边界速查卡

本 Skill 面向需要将非结构化 ESG 数据（文本、表格、URL 指向的公开页面）转换为结构化字段结果的场景。以下用一页纸说明能做什么、不能做什么。

| 维度 | 说明 |
|------|------|
| **核心输入** | 用户直接粘贴的文本段落、上传的 CSV/Excel 文件路径、公开可访问的 URL |
| **核心输出** | 按约定字段结构生成的 JSON 或 Markdown 表格，每条记录附带置信度评分 |
| **处理能力** | 单条解析、批量文件遍历、URL 批量抓取（需网络可达） |
| **字段识别** | 环境（E）、社会（S）、治理（G）三类指标的关键数值、日期、主体名称、数据来源 |
| **自定义格式** | 支持用户指定输出字段名、字段顺序、单位换算规则 |

**不能做的事项：**

- 不访问需要登录认证的内部系统或付费数据库
- 不执行数据质量修复（如缺失值插补、异常值剔除）
- 不生成趋势预测或投资建议
- 不保证识别准确率达到任何具体百分比（受原始数据质量制约）
- 不处理非文本格式（图片中的文字需先经 OCR 转换）

**适用对象：** ESG 分析师、可持续发展报告编制人员、数据治理工程师、需要快速抽取公开 ESG 指标的研究人员。


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

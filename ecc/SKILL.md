---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ecc
name: ecc
displayName: 数据转换 信息提取 结构化输出
description: 将用户提供的任意数据源转换为结构化结果，并标注置信度。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ecc
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Studio
agent_created: true
trigger_words: ["ecc", "数据转换", "结构化输出", "信息提取", "数据解析"]
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

# ECC 数据转换与结构化输出 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|--------|----------|
| **输入处理** | 用户直接粘贴的文本、上传的 CSV/JSON/Excel 文件、公开可访问的 URL 内容 | 需要登录认证的私有系统数据、加密文件、动态渲染的 JS 页面 |
| **信息提取** | 识别实体（人名/机构/日期/金额）、关键字段、表格结构、层级关系 | 理解隐含语义（如反讽、隐喻）、跨文档推理、主观判断 |
| **格式转换** | 输出为 JSON / CSV / Markdown 表格 / 自定义分隔符格式 | 生成 PDF、Word 等二进制格式文件 |
| **批量处理** | 单次请求最多处理 50 条记录或 1MB 文本 | 超过上述限制的流式处理、实时数据管道 |
| **置信度标注** | 对每个提取字段标注 high / medium / low 三级置信度 | 提供概率百分比或统计显著性检验 |

### 1.2 适用对象

- **数据分析师**：需要快速将非结构化日志、邮件、报告转为可分析的表格数据
- **业务运营人员**：需要从客户反馈、市场调研中提取结构化信息
- **开发者**：需要将外部数据源接入自有系统，但缺少现成解析器
- **研究人员**：需要从文献、访谈记录中抽取关键信息进行汇总

### 1.3 输入输出速查

| 项目 | 规格 |
|------|------|
| 输入来源 | 用户提供的数据 / 文件 / URL |
| 输出格式 | JSON（默认）、CSV、Markdown 表格、自定义分隔符 |
| 最大输入 | 50 条记录 或 1MB 文本（超出需分批） |
| 处理时间 | 单条记录 < 2 秒，50 条记录 < 30 秒 |


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

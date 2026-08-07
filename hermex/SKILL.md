---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: hermex
name: hermex
displayName: 网页数据采集 结构化提取 批量处理
description: 从网页、文件或数据中提取关键信息，按约定格式输出结构化结果。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/hermex
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["爬虫采集", "数据提取", "结构化输出", "网页抓取", "信息整理"]
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

# hermex — 网页数据采集与结构化提取 Skill

## 一、能力边界：一页纸速查卡

### ✅ 能做（5 项核心能力）

| 序号 | 能力项 | 说明 | 示例 |
|------|--------|------|------|
| 1 | 数据/文件/URL 输入解析 | 接受用户提供的文本、文件路径或网页链接作为输入源 | `https://example.com/products` |
| 2 | 关键信息识别与保留 | 从原始内容中抽取实体、属性、关系等关键要素 | 商品名称、价格、库存状态 |
| 3 | 按约定格式生成输出 | 根据用户指定的字段结构或默认模板输出结果 | JSON / CSV / Markdown 表格 |
| 4 | 置信度标注 | 对每个提取字段标注可信程度，低置信度时明确提示 | `confidence: 0.92` |
| 5 | 批量处理与自定义格式 | 支持多条目循环处理，允许用户自定义输出字段和格式 | 批量抓取 50 个商品页 |

### ❌ 不能做（明确边界）

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行 JavaScript 渲染 | 仅解析静态 HTML 内容，动态加载页面需用户先提供渲染后源码 |
| 2 | 不绕过登录/验证码 | 需要认证的页面不在处理范围内 |
| 3 | 不处理二进制文件 | 仅支持文本类文件（HTML、JSON、CSV、TXT、Markdown） |
| 4 | 不保证数据准确性 | 提取结果受源数据质量影响，低质量输入可能产生低置信度输出 |
| 5 | 不进行语义理解 | 仅做模式匹配和结构提取，不推断隐含含义 |

### 🎯 适用对象

- 需要从网页批量收集结构化数据的开发者
- 需要将非结构化文本转为表格/JSON 的数据分析人员
- 需要定期采集特定网站信息的内容运营人员


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

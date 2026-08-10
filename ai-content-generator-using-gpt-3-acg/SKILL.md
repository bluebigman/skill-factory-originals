---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ai-content-generator-using-gpt-3-acg
name: ai-content-generator-using-gpt-3-acg
displayName: 文本生成 内容创作 智能写作
description: 基于用户输入，从零生成结构化文本内容，支持批量处理与自定义格式。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ai-content-generator-using-gpt-3-acg
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["ai-content-generator-using-gpt-3-acg", "文本生成", "内容创作", "智能写作", "批量生成", "结构化输出"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# 文本生成器（ACG）技能文档

## 一、能力边界：一页纸速查卡

### ✅ 能做（核心能力清单）

| 序号 | 能力项 | 说明 | 示例 |
|------|--------|------|------|
| 1 | 数据/文件/URL 转结构化结果 | 接收用户提供的原始材料，解析并提取关键信息，输出为结构化数据 | 将一篇新闻 URL 转为摘要+关键词+情感倾向的 JSON |
| 2 | 关键信息识别与保留 | 自动识别输入中的实体、数字、日期、专有名词，并完整保留在输出中 | 从合同文本中提取甲方、乙方、金额、期限 |
| 3 | 按约定格式生成输出 | 支持用户指定的输出格式（JSON / Markdown / CSV / 纯文本） | 用户要求输出为 Markdown ，则按呈现 |
| 4 | 置信度提示 | 对不确定的字段标注置信度等级（高/中/低），不隐瞒不确定性 | `{"entity": "张三", "confidence": 0.95}` |
| 5 | 批量处理与自定义格式 | 支持一次输入多条数据，逐条处理并汇总；支持用户自定义字段结构 | 一次传入 10 条商品评论，输出 10 条情感分析结果 |

### ❌ 不能做（明确边界）

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行代码 | 不运行用户提供的脚本或程序 |
| 2 | 不访问实时网络 | 不主动抓取网页内容，仅处理用户直接提供的数据/文件/URL 文本 |
| 3 | 不保证事实准确性 | 生成内容基于输入推断，不承担事实核查责任 |
| 4 | 不处理敏感信息 | 不接收身份证号、银行卡号等个人敏感信息 |
| 5 | 不生成违法内容 | 拒绝生成违法违规、侵权、仇恨言论等内容 |

### 👥 适用对象

- 需要快速将零散文本整理为结构化数据的运营人员
- 需要批量生成文案初稿的内容创作者
- 需要从长文档中提取关键信息的研究人员
- 需要将用户输入转为标准格式的开发者


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

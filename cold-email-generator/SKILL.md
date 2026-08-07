---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: cold-email-generator
name: cold-email-generator
displayName: 冷邮件撰写 商务触达 客户开发
description: 将零散资料转化为专业冷邮件草稿，支持批量处理与置信度标注。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/cold-email-generator
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaCraft Studio
agent_created: true
trigger_words: ["邮件撰写", "cold email", "冷邮件", "商务邮件", "开发信", "outreach"]
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

# 冷邮件撰写 Skill 文档

## 一、能力边界速查卡

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入处理 | 接受用户粘贴的文本、上传的文档（.txt/.md/.csv）、公开 URL 链接 | 无法直接访问需登录验证的私有系统或付费墙内容 |
| 信息提取 | 从输入中识别收件人姓名、公司、行业、产品/服务描述、合作意向关键词 | 无法读取图片中的文字（OCR 不在本 Skill 范围内） |
| 邮件生成 | 生成结构完整的冷邮件草稿，包含主题行、称呼、正文、签名占位符 | 不负责实际发送邮件，不管理收件人列表 |
| 批量处理 | 支持一次输入多条记录（如 CSV 多行），逐条生成对应邮件 | 单次处理超过 50 条记录时可能超时，建议分批 |
| 格式定制 | 可按用户指定的字段顺序、语气风格（正式/半正式）、长度要求输出 | 无法生成 HTML 富文本邮件模板，仅输出纯文本 Markdown 格式 |
| 置信度标注 | 对不确定的信息（如推测的行业、模糊的公司名）标注 `[需核实:字段]` | 不编造缺失的关键信息（如收件人姓名） |

### 1.2 适用对象

- **适用**：销售开发代表、自由职业者、初创团队、需要批量发送商务触达邮件的个人或小团队。
- **不适用**：需要深度个性化（如基于完整 CRM 历史记录定制）、需要多语言自动翻译、需要 A/B 测试版本生成的场景。


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

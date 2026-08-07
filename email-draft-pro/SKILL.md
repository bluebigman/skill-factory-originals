---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: email-draft-pro
name: email-draft-pro
displayName: 商务邮件起草 双语模板 批量生成
description: 按场景生成专业商务邮件，自动匹配语气与格式，支持中英双语与批量起草。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/email-draft-pro
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge Studio
agent_created: true
trigger_words: ["商务邮件", "邮件起草", "email draft", "business email", "邮件模板", "邮件撰写", "商务信函"]
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

# email-draft-pro 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| **场景覆盖** | 商务邀约、客户跟进、项目汇报、会议纪要、报价说明、投诉回复、合作意向、离职告别 | 私人情感邮件、法律文书、合同正文、学术论文、营销垃圾邮件 |
| **语言支持** | 简体中文、英文（美式/英式），可中英混排 | 其他语种（需人工翻译后输入） |
| **语气控制** | 正式/半正式/亲切，自动匹配收件人关系 | 极端情绪化表达（愤怒、嘲讽、威胁） |
| **格式输出** | 纯文本、Markdown、HTML 邮件体 | PDF、Word 附件生成 |
| **批量起草** | 同一场景下多收件人批量生成（≤20封/批） | 跨场景混合批量（需分批执行） |
| **个性化** | 基于输入参数（称呼、公司名、项目名）自动填充 | 读取用户通讯录、历史邮件、日历数据 |

### 1.2 适用对象

- **职场新人**：需要标准模板快速上手
- **业务人员**：日常客户沟通、供应商联络
- **管理者**：团队汇报、跨部门协调
- **自由职业者**：客户报价、项目提案

### 1.3 输入参数速查表

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| `scenario` | string | ✅ | 邮件场景关键词 | `"客户跟进"` |
| `recipient` | string | ✅ | 收件人称呼 | `"张总"` |
| `sender` | string | ✅ | 发件人署名 | `"李明"` |
| `language` | string | ❌ | `zh` / `en`，默认 `zh` | `"en"` |
| `tone` | string | ❌ | `formal` / `semi` / `friendly`，默认 `semi` | `"formal"` |
| `context` | string | ❌ | 补充背景信息 | `"上周会议讨论过合作细节"` |
| `action_item` | string | ❌ | 期望收件人采取的行动 | `"请确认附件中的报价单"` |
| `deadline` | string | ❌ | 截止时间 | `"本周五前"` |
| `batch_list` | array | ❌ | 批量收件人列表（≤20项） | `[{"name":"王总","company":"A公司"},{"name":"刘总","company":"B公司"}]` |


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

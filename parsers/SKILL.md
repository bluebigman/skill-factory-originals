---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: parsers
name: parsers
displayName: 数据解析 信息抽取 格式转换
description: 将用户提供的文件、URL或数据解析为结构化结果，支持批量处理与置信度标注。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/parsers
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 解析工坊
agent_created: true
trigger_words: ["parsers", "解析", "PDF转文档", "数据抽取", "格式转换", "结构化输出"]
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

# parsers 技能文档

## 一、能力边界速查卡

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|--------|----------|
| 输入类型 | 用户直接粘贴的文本、上传的本地文件（PDF/Word/CSV/JSON）、公开可访问的 URL | 需要登录鉴权的私有系统、加密文件、动态渲染的网页（需额外说明） |
| 处理能力 | 抽取关键字段、识别实体与关系、按模板重组格式、批量处理同构数据 | 理解上下文隐含语义（如反讽、隐喻）、跨语言自动翻译、主观判断类任务 |
| 输出形式 | 结构化 JSON / Markdown 表格 / 自定义分隔符文本 | 直接写入用户本地文件系统（需用户自行保存） |
| 质量保障 | 对每个输出字段标注置信度（高/中/低） | 对低置信度内容给出确定性结论 |

### 1.2 适用对象

- **适合**：日志文件解析、表单数据抽取、网页信息提取、批量文件格式统一
- **不适合**：需要领域专家判断的医疗诊断、法律裁决、投资决策等场景


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

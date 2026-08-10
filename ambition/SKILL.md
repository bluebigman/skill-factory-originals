---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ambition
name: ambition
displayName: 数据洞察 信息萃取 结构化输出
description: 将任意数据源转化为结构化结果，保留关键信息并标注置信度。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: s://.com/bluebigman/skill-factory-originals/tree/main/ambition
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["ambition", "数据转换", "信息提取", "结构化输出", "数据解析"]
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

# ambition — 数据洞察与结构化输出 Skill

## 一、能力边界速查卡

本 Skill 专注于将非结构化或半结构化的输入（文本、文件、URL）转化为符合约定格式的结构化结果。以下是能力边界的一页纸说明：

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入类型 | 用户粘贴的文本、上传的 CSV/JSON/TXT 文件、可公开访问的 URL | 需要登录认证的私有系统、二进制文件（/音频/视频） |
| 核心操作 | 解析内容、识别关键字段、按模板重组、批量处理 | 执行代码、修改源文件、发起网络（仅读取） |
| 输出形式 | Markdown 、JSON 结构、CSV 行、自定义分隔符文本 | 生成图表、创建压缩包、直接写入用户磁盘 |
| 质量保障 | 对每个输出字段标注置信度（高/中/低） | 对缺失信息进行猜测或编造 |
| 批量能力 | 支持多行记录逐条处理，保持格式一致 | 跨文件关联分析、去重合并 |

**适用对象**：需要快速将零散数据整理为规范格式的运营人员、数据分析师、开发者，以及任何需要从文本中抽取结构化信息的场景。

**不适用场景**：需要深度语义理解的主观判断、需要外部知识库补全的推理任务、需要实时数据验证的场景。


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

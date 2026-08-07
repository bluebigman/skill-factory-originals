---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: dictionary-term-explain
name: 术语释义助手
displayName: 多场景术语拆解释义
description: 按场景拆解术语含义，给出边界清晰、可落地的概念解释。
version: 2.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/dictionary-term-explain
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 概念拆解工坊
agent_created: true
trigger_words: ["术语解释", "名词释义", "概念说明", "这个词什么意思", "通俗解释", "术语拆解", "概念辨析"]
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

# 术语释义助手 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 术语精确匹配 | 在本地知识库中查找术语，返回结构化解释 | 输入"区块链"，返回核心定义、场景拆解等 |
| 场景化拆解 | 按用户指定场景（技术/商业/法律/日常等）生成针对性解释 | 指定"金融场景"解释"杠杆" |
| 外部知识补充 | 本地未命中时，尝试调用维基百科 API 获取信息 | 输入"拓扑学"，本地无记录，转外部查询 |
| 结构化输出 | 输出固定格式的 Markdown 文档，含核心定义、场景拆解、边界界定、常见误用 | 见 3.3 输出规范 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不处理超长输入 | 术语长度超过 100 字符直接拒绝，返回错误码 `E1001` |
| 不编造知识 | 本地和外部均未命中时，返回错误码 `E1004`，不猜测含义 |
| 不提供多语言翻译 | 仅支持中文输入和中文输出（术语本身可为外文） |
| 不进行深度学术论证 | 提供概念性解释，不输出论文级分析或文献综述 |
| 不处理模糊多义词 | 同一术语有多个完全无关含义时，要求用户明确指定场景，否则按默认场景处理 |

### 1.3 适用对象

- 需要快速理解陌生术语的职场新人
- 跨领域协作时需要对齐概念的产品经理、设计师、工程师
- 撰写文档时需要准确界定术语边界的写作者
- 准备面试或汇报时需要清晰表达概念的学习者


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

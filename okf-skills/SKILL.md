---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: okf-skills
name: okf-skills
displayName: 数据整理 信息抽取 结构化输出
description: 将用户提供的任意数据源解析为规范结构化结果，附置信度标注。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/okf-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨
agent_created: true
trigger_words: ["okf skills", "数据整理", "信息抽取", "结构化输出", "格式转换", "数据清洗"]
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

# okf-skills 技能文档

## 一、能力边界速查卡

### 1.1 能做什么

| 编号 | 能力项 | 说明 | 典型场景 |
|------|--------|------|----------|
| C1 | 数据源解析 | 从文本、文件路径或 URL 中提取原始内容 | 用户粘贴一段日志、给出文件路径或链接 |
| C2 | 关键信息识别 | 自动定位输入中的实体、字段、数值等核心要素 | 从一段会议纪要中提取待办事项与负责人 |
| C3 | 结构化输出 | 按约定模板生成 JSON/YAML/表格等格式 | 将客户反馈整理为问题分类表 |
| C4 | 置信度标注 | 对每个输出字段标注可信程度（高/中/低） | 识别出的日期存在歧义时标注低置信度 |
| C5 | 批量与自定义 | 支持多条记录同时处理，允许用户指定输出字段 | 一次整理 50 条商品信息，自定义只输出名称和价格 |

### 1.2 不能做什么

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行外部调用 | 不主动访问网络、不调用第三方 API，仅处理用户已提供的内容 |
| L2 | 不替代专业判断 | 法律、医疗、财务等领域的结论需由专业人士复核 |
| L3 | 不保证数据真实性 | 输入数据本身的准确性由提供方负责，本技能仅做格式与结构处理 |
| L4 | 不处理加密内容 | 加密文件、密码保护文档需先由用户解密 |
| L5 | 不生成主观评价 | 只做客观整理，不输出"好/坏/推荐/不推荐"等判断 |

### 1.3 适用对象

- 需要将零散数据整理为统一格式的运营人员
- 需要从文档中快速抽取关键字段的产品经理
- 需要批量转换数据格式的开发者
- 任何有"把杂乱信息变整齐"需求的普通用户


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

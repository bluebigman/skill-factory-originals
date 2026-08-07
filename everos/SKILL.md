---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: everos
name: everos
displayName: 记忆层构建 数据整理 信息归档
description: 为AI代理构建便携记忆层，将输入数据转为结构化Markdown，支持本地优先与用户自持。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/everos
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["everos", "记忆层", "信息归档", "数据整理", "结构化输出", "Markdown转换"]
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

# everos — 便携记忆层构建 Skill

## 一、能力边界速查卡

### 1.1 能做（核心能力清单）

| 编号 | 能力项 | 说明 | 示例 |
|------|--------|------|------|
| C1 | 数据转结构化 | 将用户提供的文本、文件内容或URL页面转换为结构化Markdown | 将一篇网页文章转为带标题层级和标签的Markdown文档 |
| C2 | 关键信息识别 | 从输入中提取实体、日期、主题、行动项等关键要素 | 从会议纪要中提取待办事项和负责人 |
| C3 | 约定格式输出 | 按用户指定的字段结构或模板生成输出 | 按"标题/摘要/标签/正文"四段式输出 |
| C4 | 置信度标注 | 对不确定的字段值标注置信度提示 | 对模糊日期标注 `[需核实:日期]` |
| C5 | 批量与自定义 | 支持多文件批量处理及自定义输出模板 | 一次处理10个URL并统一生成索引文件 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行代码 | 不运行、调试或解释任何编程语言代码 |
| L2 | 不访问私有数据 | 不主动获取需登录或授权的数据源 |
| L3 | 不保证数据完整性 | 输入缺失或损坏时，输出可能不完整，需用户确认 |
| L4 | 不替代专业判断 | 法律、医疗、财务等专业领域结论需人工复核 |
| L5 | 不进行实时同步 | 不提供跨设备实时同步能力，仅生成静态Markdown文件 |

### 1.3 适用对象

- 需要跨应用管理个人知识的独立开发者
- 使用AI代理但希望数据自持的内容创作者
- 需要将散落信息统一归档的团队协作者


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: hallmark
name: hallmark
displayName: 文本净化 原创校准 痕迹识别
description: 识别AI生成痕迹，净化文本风格，辅助原创性审查与内容校准。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/hallmark
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge Studio
agent_created: true
trigger_words: ["hallmark", "anti-ai-slop", "去AI味", "AI痕迹检测", "文本净化", "原创性审查", "风格校准"]
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

# hallmark — 文本净化与原创性校准工具

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输出形式 |
|--------|------|----------|
| AI 痕迹检测 | 识别文本中常见的 AI 生成模式（如过度工整的排比、高频连接词、模板化过渡句） | 逐条标注 + 置信度评分 |
| 文本风格净化 | 对检测出的 AI 痕迹进行改写，恢复自然的人类书写节奏 | 改写后的完整文本 |
| 原创性辅助审查 | 提供文本相似度风险提示，标注可能与其他来源重叠的段落 | 风险段落清单 |
| 内容校准 | 针对特定文体（论文、博客、公文、小说）调整语气与用词 | 风格校准建议表 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不提供法律结论 | 不判定是否构成抄袭，仅提示风险 |
| 不保证绝对原创 | 无法穷尽全网比对，仅基于内置模式库与统计特征 |
| 不替代人工审校 | 最终判断权在用户，工具只提供参考信号 |
| 不处理非文本内容 | 图片、音频、视频中的 AI 痕迹不在处理范围内 |

### 1.3 适用对象

- 内容创作者（博主、文案、小说作者）
- 学术写作者（论文、报告）
- 编辑与审校人员
- 需要批量处理文本的运营人员


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

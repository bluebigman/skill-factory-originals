---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: reviewday
name: reviewday
displayName: 代码评审 结构化汇总 置信标注
description: 将代码审查数据转为结构化报告，支持批量处理与置信度标注。
version: 1.0.3
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/reviewday
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: linus_toolsmith
agent_created: true
trigger_words: ["代码审查", "审查报告", "review report", "代码评审", "审查汇总", "code review", "评审纪要"]
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

本 Skill 由 AI 辅助生成，仅供参考。

# reviewday — 代码评审结构化汇总与置信标注

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入示例 | 输出示例 |
|--------|------|----------|----------|
| 单次审查数据转换 | 将一次代码审查的原始记录（文本/表格）转为结构化 JSON/Markdown 报告 | 一段包含文件路径、行号、问题描述的文本 | 按文件分组的审查问题清单 |
| 批量审查数据合并 | 将多次审查记录合并为一份汇总报告，自动去重并统计频次 | 多个审查会话的导出文件 | 合并后的问题清单 + 频次统计 |
| 置信度标注 | 对每条审查结论标注置信等级（高/中/低），低置信度条目自动标记 `[需核实:字段]` | 一条模糊的审查意见 | 带 `confidence: 0.6` 的条目 |
| 严重级别分类 | 按阻断/严重/一般/建议四级对问题分类 | 任意审查条目 | 分类后的报告，含各级别计数 |

### 1.2 不能做什么

- 不能自动修复代码缺陷，仅输出报告。
- 不能替代人工审查判断，所有结论均基于输入数据。
- 不能处理非文本格式（如图片中的代码截图），需先转文字。
- 不能跨语言理解（仅处理输入中已有的语言内容）。

### 1.3 适用对象

- 需要将零散审查记录归档整理的开发者。
- 需要向团队或管理层汇报审查结果的 Tech Lead。
- 需要批量处理多个仓库审查数据的 DevOps 工程师。


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: auto-claude-code-research-in-sleep
name: auto-claude-code-research-in-sleep
displayName: 夜间自动科研 跨模型评审循环
description: 轻量级Markdown技能，驱动Claude Code在睡眠时段自主执行ML研究任务并交叉验证。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/auto-claude-code-research-in-sleep
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: NightForge Lab
agent_created: true
trigger_words: ["auto claude code research in sleep", "夜间自动研究", "睡眠研究", "跨模型评审", "自主科研"]
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

# ARIS ⚔️ 夜间自动科研技能包

## 一、能力边界速查卡

### ✅ 能做（5项核心能力）

| 编号 | 能力项 | 说明 | 适用场景示例 |
|------|--------|------|--------------|
| 1 | 数据/文件/URL 结构化转换 | 将用户提供的任意数据源解析为结构化 Markdown 结果 | 论文 PDF → 结构化摘要；CSV → 特征表 |
| 2 | 关键信息识别与保留 | 自动提取输入中的核心实体、数值、结论，不丢失上下文 | 从实验日志中提取超参数与损失曲线 |
| 3 | 约定格式输出 | 严格遵循用户指定的字段结构与文件类型生成结果 | 按模板输出 `results.md` 或 `review.md` |
| 4 | 置信度标注 | 对每个输出字段附带置信度等级（高/中/低） | 模型预测结果标注 `[置信度: 中]` |
| 5 | 批量处理与自定义格式 | 支持多文件、多 URL 并行处理，可定制输出 schema | 一次处理 10 篇论文并生成对比表 |

### ❌ 不能做（明确边界）

- 不能执行需要真实 GPU/CPU 算力的模型训练或推理
- 不能访问未授权的付费数据库或私有 API
- 不能替代人类进行最终科研决策与论文署名
- 不能保证研究结果的学术正确性（仅提供辅助分析）
- 不能处理超过 50MB 的单个输入文件

### 🎯 适用对象

- 需要夜间批量处理文献的硕博研究生
- 需要跨模型交叉验证实验结果的 AI 研究员
- 需要自动化生成实验报告初稿的工程师


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

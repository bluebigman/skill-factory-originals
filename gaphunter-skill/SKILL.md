---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: gaphunter-skill
name: gaphunter-skill
displayName: 竞品审查 差距分析 报告生成
description: 将竞品数据转化为结构化差距分析报告，支持过滤与PDF导出。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/gaphunter-skill
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: skill-forge-studio
agent_created: true
trigger_words: ["代码审查", "竞品分析", "差距分析", "gap analysis", "competitor review", "功能对比", "差异分析"]
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

# gaphunter-skill 技能文档

## 一、能力边界速查卡

### ✅ 能做（5项核心能力）

| 编号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| 1 | 数据摄取与解析 | 接受用户提供的文件、URL或直接粘贴的文本数据，自动识别格式（CSV/JSON/Markdown表格/纯文本） | `data.csv`、`https://example.com/features` |
| 2 | 关键信息提取 | 从原始数据中抽取竞品名称、功能点、版本号、发布时间、优劣势描述等核心字段 | 一段包含竞品功能描述的文本 |
| 3 | 差距识别与标注 | 对比基准产品与竞品的功能覆盖情况，标记"已覆盖/未覆盖/部分覆盖"三种状态 | 两份功能清单 |
| 4 | 结构化报告生成 | 按固定模板输出HTML格式的差距分析报告，包含摘要、明细表、差异高亮 | 无（自动生成） |
| 5 | 过滤与导出 | 支持按状态（已覆盖/未覆盖）、按竞品名称过滤报告内容；支持导出为PDF文件 | `--filter=未覆盖`、`--export=pdf` |

### ❌ 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不自动抓取网页 | 需要用户主动提供URL内容或文件，不执行网络爬虫行为 |
| 2 | 不生成主观建议 | 只输出客观差距事实，不提供"应该怎么做"的策略建议 |
| 3 | 不处理非文本数据 | 图片、音频、视频中的信息需用户先转成文字 |
| 4 | 不保证数据准确性 | 输入数据本身的错误会直接反映在输出中，不进行二次校验 |
| 5 | 不执行实时对比 | 所有对比基于用户提供的静态数据快照，不连接外部数据库 |

### 👥 适用对象

- 产品经理：快速梳理竞品功能覆盖度
- 技术负责人：评估技术方案与竞品的差距
- 市场分析师：整理竞品宣传卖点差异
- 创业者：验证产品定位与市场现有方案的差异


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: spec-driven-develop
name: spec-driven-develop
displayName: 规格驱动开发 架构先行 任务拆解
description: 将需求规格转化为结构化开发计划与任务清单的流程型技能。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/spec-driven-develop
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Ling
agent_created: true
trigger_words: ["spec-driven-develop", "规格驱动开发", "需求转任务", "架构先行", "开发计划拆解"]
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

# 规格驱动开发（Spec-Driven Develop）

## 一、能力边界：一页纸速查卡

| 维度 | 说明 |
|------|------|
| **核心用途** | 将用户提供的需求规格（文本/文件/URL）转化为结构化的开发计划、任务分解清单与 GitHub Issue/PR 模板 |
| **输入来源** | 用户直接粘贴的文本、上传的 `.md/.txt/.json` 文件、可公开访问的 URL |
| **输出产物** | ① 架构决策记录（ADR）摘要 ② 任务分解清单（含依赖关系） ③ GitHub Issue 模板 ④ PR 描述模板 |
| **处理上限** | 单次处理不超过 5000 字或 100 个需求点；超出部分需分批处理 |
| **时间预估** | 每个任务项预估耗时范围（小时），不承诺精确工期 |

### ✅ 能做（5 项核心能力）

1. **需求解析**：从输入中提取功能点、约束条件、验收标准，识别模糊表述。
2. **架构规划**：基于功能点给出模块划分建议，标注模块间依赖关系。
3. **任务拆解**：将功能点拆分为可执行的开发任务，每个任务包含输入/输出/验收标准。
4. **GitHub 产物生成**：输出符合 GitHub 规范的 Issue 标题、标签建议、PR 描述模板。
5. **置信度标注**：对每个提取项标注置信度（高/中/低），低置信度项明确提示需人工确认。

### ❌ 不能做（边界声明）

- 不编写具体业务代码实现。
- 不评估技术选型的优劣，仅按用户给定技术栈进行规划。
- 不替代项目经理做优先级排序，仅提供依赖关系建议。
- 不处理二进制文件（图片/PDF 扫描件），仅支持纯文本与 Markdown。
- 不承诺开发周期或成功率，仅提供任务耗时估算范围。

### 适用对象

- 独立开发者：需要将模糊想法快速转化为可执行任务清单。
- 小团队技术负责人：需要将 PRD 拆解为 GitHub Issue 并分派。
- AI 辅助编程用户：需要为 AI 编码助手提供结构化任务输入。


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

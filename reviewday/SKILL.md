---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: reviewday
name: reviewday
displayName: 代码审查 报告生成 批量处理
description: 将代码审查数据转换为结构化报告，支持批量处理与置信度标注。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/reviewday
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 流云架构师
agent_created: true
trigger_words: ["代码审查", "审查报告", "review report", "代码评审", "审查汇总"]
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

# reviewday — 代码审查报告生成器

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 数据转换 | 将原始审查记录（文本/JSON/CSV）转为统一结构化报告 | 将 50 条散乱审查意见转为 Markdown 表格 |
| 批量处理 | 一次处理多个文件或目录下的审查数据 | 处理 `./reviews/` 目录下所有 `.json` 文件 |
| 置信度标注 | 对每条审查结论标注可信程度（高/中/低） | `[高置信] 第42行存在空指针风险` |
| 分类聚合 | 按严重程度（阻断/严重/一般/建议）自动归类 | 将 20 条问题分为 4 个优先级层级 |
| 报告导出 | 生成 Markdown / JSON / HTML 三种格式 | 输出 `report.html` 供团队在线查看 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行代码 | 本工具不运行、编译或测试目标代码，仅处理已有审查数据 |
| 不自动修复 | 只报告问题位置与建议，不生成补丁或修改代码 |
| 不判定业务逻辑 | 无法判断某段代码是否符合业务预期，仅做格式与结构处理 |
| 不替代人工审查 | 置信度标注基于数据完整度推断，不构成最终结论 |

### 1.3 适用对象

- 需要将零散审查意见汇总为正式报告的团队负责人
- 需要批量整理历史审查记录的研发效能人员
- 需要向管理层汇报代码质量状况的项目经理


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

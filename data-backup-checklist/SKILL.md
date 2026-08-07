---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: data-backup-checklist
name: data-backup-checklist
displayName: 备份核验 差异追踪 恢复演练
description: 备份清单核对、版本差异追踪、恢复演练评分与风险分级预警。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/data-backup-checklist
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["data-backup-checklist", "备份检查", "备份核对", "备份完整性", "备份清单", "恢复演练", "备份差异"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# 备份核验与恢复演练技能手册

## 一、能力边界（一页纸速查卡）

### 1.1 本技能能做什么

| 能力项 | 具体说明 | 输出物 |
|--------|----------|--------|
| 备份清单核对 | 对照预定义清单逐项检查备份任务是否按计划执行 | 核对结果表（含通过/未通过/警告） |
| 版本差异追踪 | 对比两个时间点的备份版本，列出新增、删除、变更的文件/数据项 | 差异报告（含变更类型与数量统计） |
| 恢复演练评分 | 对恢复演练过程按预设评分规则打分，输出总分与分项得分 | 评分明细表（含扣分原因） |
| 风险分级预警 | 根据核对与演练结果，将备份体系风险分为低/中/高三级，并给出处置建议 | 风险等级判定书（含建议动作） |

### 1.2 本技能不能做什么

- 不能直接执行备份操作或触发备份任务
- 不能代替人工判断备份数据的业务价值
- 不能自动修复备份失败或数据损坏问题
- 不能对未提供完整信息的备份环境做确定性结论
- 不能跨系统读取备份日志（需用户提供或导入）

### 1.3 适用对象

| 角色 | 使用场景 |
|------|----------|
| 运维工程师 | 日常备份任务巡检、月度备份合规自查 |
| 数据管理员 | 备份版本变更分析、恢复演练组织与评分 |
| 技术主管 | 备份体系风险评审、改进优先级排序 |


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

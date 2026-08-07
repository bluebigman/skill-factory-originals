---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: data-backup-checklist
name: data-backup-checklist
displayName: 备份巡检 完整性核对 恢复演练
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
trigger_words: ["data-backup-checklist", "备份检查", "备份核对", "备份完整性", "备份巡检", "恢复演练评分"]

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

# 备份巡检与恢复演练助手（data-backup-checklist）

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 编号 | 能力项 | 具体说明 |
|------|--------|----------|
| C1 | 备份清单核对 | 对照预设清单逐项检查备份任务是否覆盖关键数据源，输出缺失项清单 |
| C2 | 版本差异追踪 | 对比相邻备份版本的文件数量、大小、时间戳，识别异常增量或缺失版本 |
| C3 | 恢复演练评分 | 按恢复时间目标（RTO）和恢复点目标（RPO）对演练结果打分，输出达标率 |
| C4 | 风险分级预警 | 根据备份失败次数、恢复成功率、存储健康度等维度，输出红/黄/绿三级风险信号 |

### 1.2 不能做什么

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行实际备份操作 | 本技能仅做检查与评估，不触发备份任务或修改备份策略 |
| L2 | 不连接生产环境 | 所有输入需由用户提供数据快照或日志文件，技能不主动访问外部系统 |
| L3 | 不预测未来故障 | 风险分级基于历史数据，不承诺对未来事件的预判能力 |
| L4 | 不替代专业审计 | 输出结果供参考，不构成合规审计或法律证据 |

### 1.3 适用对象

- 运维工程师：日常备份巡检与异常排查
- 数据管理员：定期核对备份策略与执行情况
- 技术管理者：评估恢复演练效果与整体备份健康度


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

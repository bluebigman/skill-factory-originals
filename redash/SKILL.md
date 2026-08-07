---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: redash
name: redash
displayName: 数据洞察 可视化 仪表板构建
description: 将数据源连接、查询与可视化配置转化为结构化交付物，辅助快速搭建数据看板。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/redash
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataCraft Studio
agent_created: true
trigger_words: ["数据可视化", "redash", "仪表板", "数据看板", "图表生成", "数据连接"]
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

# Redash 数据可视化与仪表板构建 Skill

## 一、能力边界速查卡

### 1.1 本 Skill 能做什么

| 序号 | 能力项 | 说明 | 适用场景示例 |
|------|--------|------|--------------|
| 1 | 数据源接入方案设计 | 根据用户提供的数据源类型（数据库、API、文件等），输出连接配置建议与查询策略 | 用户说"我想连 MySQL 做销售分析" |
| 2 | 查询语句结构化整理 | 将用户提供的 SQL 或数据提取逻辑，整理为可执行的查询方案，并标注关键字段 | 用户粘贴一段 SQL 要求优化或解释 |
| 3 | 可视化图表类型匹配 | 根据数据特征（维度/度量、时间序列、占比等），推荐合适的图表类型并说明理由 | 用户问"这种数据用什么图展示好" |
| 4 | 仪表板布局规划 | 基于业务指标优先级，输出仪表板区块划分、图表排列顺序与交互联动建议 | 用户要求"帮我设计一个运营监控看板" |
| 5 | 数据刷新与共享策略 | 针对定时刷新、权限管理、分享链接等需求，给出配置参数建议 | 用户问"怎么让团队每天自动看到最新数据" |

### 1.2 本 Skill 不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行实际数据连接 | 本 Skill 仅输出方案与配置建议，不代替用户操作 Redash 实例 |
| 2 | 不编写完整业务代码 | 不生成完整的 Python/JavaScript 脚本，仅提供查询片段或配置参数 |
| 3 | 不保证数据准确性 | 不验证用户提供数据的真实性、完整性，输出结果依赖输入质量 |
| 4 | 不提供部署运维指导 | 不涉及 Redash 服务器安装、Docker 配置、K8s 部署等基础设施内容 |
| 5 | 不替代数据分析决策 | 仅提供可视化呈现方案，不输出业务结论或趋势预测 |

### 1.3 适用对象

- 需要快速搭建数据看板的产品经理、运营人员
- 希望规范查询与可视化流程的数据分析师
- 初次接触 Redash 工具、需要配置指引的技术人员


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

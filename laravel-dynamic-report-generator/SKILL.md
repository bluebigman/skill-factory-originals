---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: laravel-dynamic-report-generator
name: laravel-dynamic-report-generator
displayName: 动态报表 数据透视 可视化输出
description: 将用户数据转化为结构化报表，支持动态查询与可视化输出。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/laravel-dynamic-report-generator
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据工坊
agent_created: true
trigger_words: ["报表", "数据可视化", "laravel dynamic report generator", "动态报表", "数据透视", "数据洞察", "统计图表", "报告生成"]
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

# Laravel 动态报表生成器 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 动态查询 | 根据用户传入的筛选条件，实时构建数据库查询 | 按日期范围、状态、分类筛选订单数据 |
| 结构化报表 | 将查询结果整理为表格、分组、汇总等结构化格式 | 月度销售汇总表、用户活跃度统计表 |
| 可视化输出 | 生成图表数据（柱状图、折线图、饼图）所需的 JSON 结构 | 趋势图数据、占比分布数据 |
| 数据透视 | 支持按维度（时间、分类、地区）进行多角度聚合 | 按月份×产品类别的销售额矩阵 |
| 导出支持 | 输出可被前端图表库直接消费的数据格式 | ECharts、Chart.js 兼容的数据结构 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行写操作 | 仅生成报表数据，不执行 INSERT/UPDATE/DELETE |
| 不处理非结构化数据 | 仅支持关系型数据库中的结构化数据 |
| 不提供实时推送 | 报表为请求-响应模式，不主动推送更新 |
| 不包含权限系统 | 数据权限需由调用方自行控制 |
| 不生成物理文件 | 输出为内存中的数据结构，不直接生成 PDF/Excel 文件 |

### 1.3 适用对象

- Laravel 开发者：需要快速为业务模块添加报表功能
- 数据分析人员：需要从业务数据中提取洞察
- 产品经理：需要验证数据展示方案的可行性


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

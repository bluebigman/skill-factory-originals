---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: canvasxpress
name: canvasxpress
displayName: 数据分析 可视化 审计追踪
description: 将数据文件转为可交互图表，并保留完整操作审计记录。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/canvasxpress
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingDataWorks
agent_created: true
trigger_words: ["数据可视化", "canvasxpress", "图表生成", "审计追踪", "数据分析", "交互式图表"]
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

# CanvasXpress 数据分析与可视化 Skill 文档

## 一、能力边界（一页纸速查卡）

### 能做（核心能力）

| 编号 | 能力项 | 说明 | 适用场景 |
|------|--------|------|----------|
| 1 | 数据文件解析 | 读取 CSV / TSV / JSON / Excel 格式数据，识别字段类型与结构 | 用户提供本地数据文件 |
| 2 | URL 数据抓取 | 从公开 URL 获取数据源，自动判断格式并解析 | 用户提供数据链接 |
| 3 | 图表类型推荐 | 根据数据维度、字段类型、分析目标，推荐合适的图表类型（散点、柱状、热力图、箱线图等） | 用户不确定用什么图 |
| 4 | 审计追踪生成 | 记录数据加载、转换、绘图每一步操作，输出可追溯的审计日志 | 科研、合规、教学场景 |
| 5 | 批量图表输出 | 支持多组数据一次性生成多个图表，输出为独立 HTML 文件或合并报告 | 多变量对比分析 |

### 不能做（明确限制）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行数据清洗 | 缺失值填充、异常值剔除等操作需用户预先完成，或明确指示后由用户确认再执行 |
| 2 | 不进行统计建模 | 回归、聚类、降维等统计计算不在本 Skill 范围内，仅做可视化呈现 |
| 3 | 不连接私有数据库 | 仅支持用户直接提供的数据文件或公开 URL，不接入任何数据库系统 |
| 4 | 不生成动态交互逻辑 | 图表为静态交互（悬停提示、缩放、框选），不包含自定义 JavaScript 事件绑定 |
| 5 | 不支持实时流数据 | 仅处理静态数据集，不支持 WebSocket 或实时数据推送 |

### 适用对象

- 需要快速将数据转为可视化图表的科研人员、数据分析师
- 需要审计追踪记录的教学场景（学生提交作业、实验记录）
- 需要合规性数据操作记录的企事业单位


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

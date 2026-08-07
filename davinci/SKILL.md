---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: davinci
name: davinci
displayName: 数据可视化 智能解析 图表生成
description: 将用户数据文件URL解析为结构化结果，支持批量与自定义格式输出。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/davinci
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Ling Xiao
agent_created: true
trigger_words: ["数据可视化", "数据解析", "图表生成", "数据转换", "可视化服务"]
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

# Davinci 数据可视化服务 Skill 文档

## 一、能力边界速查卡

### 1.1 能做什么

| 编号 | 能力项 | 说明 | 适用场景示例 |
|------|--------|------|--------------|
| C1 | 数据/文件/URL 解析 | 从用户提供的 CSV、JSON、Excel、网页链接中提取结构化数据 | 用户上传销售报表，提取各区域销售额 |
| C2 | 关键信息识别与保留 | 自动识别表头、数据类型、时间字段、数值字段，保留原始语义 | 从杂乱日志中提取时间戳与错误码 |
| C3 | 约定格式输出 | 按用户指定的模板或默认模板生成统一结构的结果 | 将多份周报统一为固定字段的汇总表 |
| C4 | 置信度标注 | 对每个输出字段附加置信度等级（高/中/低） | 字段值缺失时标注"低置信度"并说明原因 |
| C5 | 批量处理与自定义格式 | 支持多文件批量输入，支持用户自定义输出字段结构 | 一次处理 20 个门店的销售数据，按自定义维度汇总 |

### 1.2 不能做什么

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行数据清洗 | 不自动删除重复行、不填充缺失值（仅标注） |
| L2 | 不生成图表文件 | 本 Skill 输出结构化数据，不产出 PNG/SVG 等图片文件 |
| L3 | 不访问需登录的 URL | 仅支持公开可访问的链接 |
| L4 | 不处理超过 50MB 的单个文件 | 超出时提示用户拆分 |
| L5 | 不进行数据趋势预测 | 仅做解析与整理，不做统计分析或预测 |

### 1.3 适用对象

- 需要快速将原始数据转为统一格式的运营人员
- 需要批量整理多来源数据报表的财务/分析人员
- 需要将网页表格数据提取为本地结构化文件的开发者


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

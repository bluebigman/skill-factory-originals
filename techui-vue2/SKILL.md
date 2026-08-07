---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: techui-vue2
name: techui-vue2
displayName: 数据可视化 大屏搭建 动态图表
description: 基于Vue2与Vite的SVG动态数据可视化大屏开发辅助工具。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/techui-vue2
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["数据可视化", "大屏", "SVG图表", "Dashboard", "Vue2图表", "可视化大屏"]
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

# TechUI Vue2 数据可视化开发辅助 Skill

## 一、能力边界速查卡

本 Skill 面向使用 **TechUI**（基于 Vite + Vue2 的动态 SVG 数据可视化大屏开发工具）的开发者，提供从数据接入到图表配置的辅助支持。

### 能做（核心能力）

| 编号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| 1 | 数据文件解析 | 将 CSV/JSON/URL 数据源转换为结构化图表数据 | `sales_data.csv`、`https://api.example.com/data` |
| 2 | 关键字段识别 | 自动识别时间、数值、类别等图表映射字段 | `{date, revenue, region}` |
| 3 | 图表配置生成 | 输出 TechUI 组件可用的配置对象 | 柱状图、折线图、饼图配置 |
| 4 | 置信度标注 | 对不确定的字段映射给出 `[需核实:字段名]` 提示 | 字段名模糊时 |
| 5 | 批量数据转换 | 支持多文件/多数据源批量处理 | 10 个 CSV 文件批量转换 |

### 不能做（明确边界）

- 不能直接运行或调试 TechUI 项目代码
- 不能替代 TechUI 官方文档（组件 API 以官方为准）
- 不能处理非结构化文本（如 PDF 报告、扫描件）
- 不能保证生成配置在特定版本下的兼容性（版本差异需自查）
- 不能自动部署或发布可视化大屏

### 适用对象

- 使用 TechUI 的 Vue2 开发者
- 需要快速将数据源接入大屏的 BI 分析师
- 正在评估 TechUI 与现有项目集成的技术选型人员


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: appmetrics-dash
name: appmetrics-dash
displayName: 应用指标 数据可视化 性能监控
description: 将Node.js应用指标数据转化为可视化图表，辅助性能分析与问题定位。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/appmetrics-dash
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["appmetrics-dash", "数据可视化", "Node.js监控", "应用指标", "性能看板", "指标仪表盘"]

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

# appmetrics-dash — 应用指标可视化 Skill 文档

## 1. 能力边界（一页纸速查卡）

### 1.1 能做什么

| 序号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| 1 | 指标数据解析 | 读取用户提供的 JSON/CSV 格式的 Node.js 应用指标数据（如事件循环延迟、内存占用、HTTP 吞吐量） | `{"eventloop": 1.2, "memory": {"rss": 52428800}}` |
| 2 | 数据文件/URL 接入 | 支持从本地文件路径或远程 URL 拉取指标数据源 | `./metrics.json` 或 `https://example.com/metrics` |
| 3 | 结构化结果生成 | 将原始指标转换为带时间戳、指标名、数值、单位的规范化记录 | `[{ "timestamp": 1699999999, "metric": "cpu", "value": 42.5, "unit": "%" }]` |
| 4 | 关键信息识别与保留 | 自动识别进程 ID、应用名称、Node 版本等元数据，并在输出中保留 | `{"app": "order-service", "pid": 1234}` |
| 5 | 批量处理与自定义格式 | 支持多文件批量转换，允许用户指定输出字段顺序或过滤条件 | 批量传入 10 个 JSON 文件，输出仅含 `cpu` 和 `memory` 字段 |

### 1.2 不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行实时采集 | 本 Skill 不主动连接 Node.js 进程或启动 appmetrics 探针，仅处理用户提供的数据 |
| 2 | 不生成图表图片 | 输出为结构化文本/表格，不渲染 PNG/SVG 图像 |
| 3 | 不进行趋势预测 | 不基于历史数据推断未来指标走向 |
| 4 | 不处理非指标数据 | 日志文本、堆栈跟踪等非结构化内容不在处理范围内 |
| 5 | 不修改原始数据 | 所有转换均为只读操作，不写回源文件 |

### 1.3 适用对象

- 使用 Node.js 构建后端服务的开发者
- 需要快速查看指标数据结构的运维人员
- 希望将 appmetrics 输出转换为统一格式以便导入其他工具的自动化脚本编写者


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: toggl-tally
name: toggl-tally
displayName: 工时统计 数据清洗 结构化输出
description: 将用户提供的工时数据、文件或链接，转换为规范结构化结果。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/toggl-tally
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据工坊
agent_created: true
trigger_words: ["toggl tally", "工时统计", "时间追踪", "数据整理", "tally 处理"]

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

# Toggl Tally 工时数据整理技能

## 一、能力边界（一页纸速查卡）

本技能面向需要快速整理 Toggl Tally 相关工时数据的用户，提供从原始输入到结构化输出的完整处理链路。

### 1.1 能做清单

| 序号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 数据解析 | 从用户提供的文本、文件（CSV/JSON/TXT）或 URL 中提取工时记录 |
| 2 | 关键信息识别 | 自动识别项目名称、任务描述、时间戳、时长、标签等核心字段 |
| 3 | 结构化输出 | 按约定模板生成统一格式的结果，支持 Markdown 表格或 JSON |
| 4 | 置信度标注 | 对每一条输出记录标注置信度等级（高/中/低），不确定字段显式标记 |
| 5 | 批量处理 | 支持多条记录同时处理，自动去重与排序 |

### 1.2 不能做清单

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不连接真实 API | 本技能不发起网络请求，不访问 Toggl 官方接口 |
| 2 | 不修改原始数据 | 所有处理均在内存中完成，不写回源文件 |
| 3 | 不推断缺失时长 | 若输入缺少时间信息，输出中标注 `[需核实:时长]`，不自行估算 |
| 4 | 不处理非工时数据 | 与时间追踪无关的内容（如财务计算、项目管理排期）不在处理范围内 |
| 5 | 不保证数据准确性 | 输出质量取决于输入质量，输入有误则输出相应有误 |

### 1.3 适用对象

- 需要将零散工时记录整理为统一格式的团队助理
- 需要从导出文件中提取关键信息做周报/月报的运营人员
- 需要将 Toggl Tally 数据转换为其他系统可导入格式的开发者


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

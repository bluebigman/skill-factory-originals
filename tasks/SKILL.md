---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: tasks
name: tasks
displayName: 数据转换 批量处理 结构化输出
description: 将各类数据源转换为结构化结果，支持批量处理与自定义格式输出。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/tasks
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨研
agent_created: true
trigger_words: ["tasks", "任务处理", "数据转换", "批量处理", "结构化输出", "数据整理", "格式转换"]
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

# tasks — 数据转换与批量处理 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 数据源解析 | 从文本、CSV、JSON、Markdown 表格等常见格式中提取原始数据 | 从一段对话中提取客户名单 |
| 结构化转换 | 将非结构化数据映射为字段明确的表格或 JSON 对象 | 将日志文本转为 `{时间, 级别, 消息}` 记录 |
| 批量处理 | 对多条同类数据执行相同的转换规则 | 一次处理 100 条订单记录 |
| 自定义格式输出 | 按用户指定的模板或字段顺序输出结果 | 输出为 Markdown 表格、CSV 或 JSON |
| 字段映射与重命名 | 将源字段名映射为目标字段名 | `name → 姓名` |
| 数据清洗（基础） | 去除空行、去重、格式统一（如日期格式） | `2024/1/1 → 2024-01-01` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行代码 | 本 Skill 仅做文本层面的转换，不运行脚本或程序 |
| 不访问外部数据源 | 无法主动读取文件、数据库或网络接口，只能处理用户提供的内容 |
| 不做语义理解 | 无法判断数据含义是否正确，仅做结构转换 |
| 不做复杂计算 | 不支持聚合统计、公式运算等逻辑 |
| 不保证数据完整性 | 源数据缺失字段时，输出中会以占位符标记，不自动补全 |

### 1.3 适用对象

- 需要将零散信息整理为表格的运营人员
- 需要将日志或导出数据转为统一格式的开发者
- 需要批量整理问卷、反馈、名单等文本数据的普通用户


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

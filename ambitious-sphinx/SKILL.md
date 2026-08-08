---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ambitious-sphinx
name: ambitious-sphinx
displayName: 数据转换 结构化处理 批量解析
description: 将任意输入数据转换为结构化结果，支持批量与自定义格式。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ambitious-sphinx
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据工坊
agent_created: true
trigger_words: ["ambitious-sphinx", "数据转换", "结构化处理", "批量解析", "格式转换"]
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

# ambitious-sphinx 技能文档

## 一、能力边界速查卡

本技能用于将用户提供的原始数据（文本、文件、URL）转换为符合约定模式的结构化结果。以下内容帮助你在 30 秒内判断此技能是否适用于当前任务。

### 能做（核心能力）

| 编号 | 能力项 | 说明 | 适用场景举例 |
|------|--------|------|--------------|
| 1 | 数据解析与结构化 | 从文本、CSV、JSON、URL 页面中提取关键字段，重组为统一结构 | 从网页抓取产品信息并整理为表格 |
| 2 | 关键信息识别与保留 | 自动识别输入中的实体、数值、日期、ID 等核心要素，不丢失原始语义 | 从客户反馈中提取订单号、问题类型、紧急程度 |
| 3 | 约定格式输出 | 根据用户指定的字段结构或预设模板生成输出文件（JSON/CSV/Markdown） | 将散乱日志转换为标准 JSON 数组 |
| 4 | 置信度标注 | 对每个输出字段标注可信程度（高/中/低），不确定时明确提示 | 当来源数据缺失时，标注 `[需核实:字段名]` |
| 5 | 批量处理与自定义格式 | 支持多文件/多 URL 输入，允许用户自定义分隔符、字段映射规则 | 一次处理 100 个 CSV 文件并统一格式 |

### 不能做（明确边界）

- 不能理解隐含语义：仅处理显式提供的数据，不推测未提及的信息
- 不能执行外部操作：不发送网络请求、不修改源文件、不调用第三方 API
- 不能处理无结构二进制：不支持图片、音频、视频内容的直接解析
- 不能保证数据准确性：输出结果依赖输入质量，输入有误则结果有误

### 适用对象

- 需要将非结构化文本转为表格数据的运营人员
- 需要批量整理多来源数据的分析人员
- 需要统一接口格式的开发者


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

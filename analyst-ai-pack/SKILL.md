---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: analyst-ai-pack
name: analyst-ai-pack
displayName: 数据分析 智能处理 结构化输出
description: 将用户提供的任意数据源解析为结构化结果，并标注置信度。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/analyst-ai-pack
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataFlow Studio
agent_created: true
trigger_words: ["analyst ai pack", "数据分析", "数据解析", "结构化输出", "批量处理", "数据转换"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# analyst-ai-pack 技能文档

## 一、能力边界速查卡

### 1.1 能做什么

| 编号 | 能力项 | 说明 | 适用场景示例 |
|------|--------|------|--------------|
| C1 | 数据源解析 | 从用户提供的文本、文件路径或 URL 中提取关键信息 | 解析 CSV 文件中的销售记录 |
| C2 | 结构化转换 | 将非结构化输入转换为约定的字段结构 | 将日志文本转为 JSON 对象 |
| C3 | 关键信息保留 | 在转换过程中不丢失原始语义 | 保留日期、金额、编号等核心字段 |
| C4 | 置信度标注 | 对每个输出字段给出可信度评估 | 标注"高/中/低"或百分比 |
| C5 | 批量与自定义 | 支持多文件处理及用户自定义输出模板 | 一次处理 10 个 URL 并统一输出 |

### 1.2 不能做什么

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行代码 | 本技能不运行用户提供的脚本或程序 |
| L2 | 不访问外网 | 除非用户明确提供 URL 内容，否则不主动抓取网络资源 |
| L3 | 不修改原始文件 | 所有操作均在内存副本上进行，不写回源文件 |
| L4 | 不保证绝对准确 | 对模糊输入，输出将包含置信度提示，不承诺 100% 正确 |

### 1.3 适用对象

- 需要快速将零散数据整理为统一格式的运营人员
- 需要批量处理数据文件的分析师
- 需要将外部数据导入内部系统的开发人员


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

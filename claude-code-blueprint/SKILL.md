---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: claude-code-blueprint
name: claude-code-blueprint
displayName: 蓝图解析 结构化转换 批处理
description: 将用户提供的任意数据、文件或URL转换为结构化结果，支持批量处理与自定义格式。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/claude-code-blueprint
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["claude code blueprint", "蓝图转换", "结构化输出", "批量解析", "数据整理"]
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

# claude-code-blueprint 技能文档

## 一、能力边界速查卡

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| **输入处理** | 用户直接粘贴的文本数据、本地文件路径（.csv/.json/.txt/.md）、公开可访问的URL | 需要登录认证的私有资源、二进制大文件（>10MB）、实时流式数据 |
| **核心转换** | 将半结构化/非结构化内容转换为字段明确的表格或JSON结构 | 对图片、音频、视频内容进行语义理解 |
| **信息保留** | 自动识别并保留输入中的关键字段（如ID、日期、金额、状态标记） | 对缺失字段进行推测性补全（会明确标注） |
| **输出格式** | 支持 Markdown 表格、JSON、CSV 三种默认格式，可自定义字段顺序与命名 | 生成可视化图表、交互式仪表盘 |
| **批量能力** | 单次最多处理 50 条独立记录，自动编号并汇总 | 跨文件关联分析、多源数据融合去重 |

### 1.2 适用对象

- **适合**：需要快速将散乱数据整理为规范表格的运营人员、需要批量提取URL页面关键信息的研究者、需要统一数据格式的开发者。
- **不适合**：需要深度语义理解或情感分析的场景、需要实时数据同步的场景。


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

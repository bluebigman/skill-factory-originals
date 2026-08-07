---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: awesome-go
name: awesome-go
displayName: Go资源导航 学习参考 项目速查
description: 面向Go开发者的学习资源导航与项目速查工具，提供结构化信息整理与输出。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/awesome-go
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: skillcraft-studio
agent_created: true
trigger_words: ["awesome go", "go资源", "go项目列表", "go学习资料", "go awesome"]
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

# awesome-go 技能文档

## 一、能力边界速查卡

### 1.1 能做（核心能力清单）

| 编号 | 能力项 | 说明 | 适用场景示例 |
|------|--------|------|--------------|
| C1 | 数据/文件/URL 结构化转换 | 将用户提供的任意格式输入（文本、文件路径、网页链接）解析为统一的结构化数据 | 用户粘贴一段 Go 项目描述，要求整理成条目 |
| C2 | 关键信息识别与保留 | 从输入中提取项目名称、分类、描述、星标数、维护状态等核心字段 | 用户给出一堆 GitHub 链接，需要提取项目名和简介 |
| C3 | 约定格式输出 | 按 Markdown 表格、JSON、或纯文本列表等指定格式生成结果 | 用户要求"输出成表格"或"输出成 JSON" |
| C4 | 置信度标注 | 对无法完全确定的信息标注置信度等级，不隐瞒不确定性 | 项目维护状态无法确认时标注"待核实" |
| C5 | 批量处理与自定义格式 | 支持一次处理多条记录，并允许用户自定义输出字段和排序规则 | 用户要求"按星标数降序，只要前 20 条" |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不实时抓取网络数据 | 本技能不主动访问互联网获取最新数据，仅处理用户提供的内容 |
| L2 | 不评估代码质量 | 不判断某个 Go 库的代码好坏、性能优劣，仅做信息整理 |
| L3 | 不推荐具体选型 | 不给出"你应该用 X 库"的结论性建议，只呈现事实信息 |
| L4 | 不生成代码 | 不编写 Go 代码、不提供代码示例 |
| L5 | 不保证信息时效性 | 输入数据可能过时，输出结果仅反映输入内容本身 |

### 1.3 适用对象

- **Go 初学者**：需要一份结构化的学习资源清单
- **Go 进阶开发者**：需要按类别检索特定领域的开源项目
- **技术调研人员**：需要快速整理 Go 生态中的项目信息


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: glowstick
name: glowstick
displayName: 实时绘图 数据可视化 OpenGL图表
description: 将数据快速转为实时OpenGL图表，支持文件与URL输入。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/glowstick
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Ling Zhang
agent_created: true
trigger_words: ["glowstick", "实时绘图", "OpenGL图表", "数据可视化", "graphing"]
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

# glowstick — 实时 OpenGL 绘图 Skill 文档

## 一、能力边界（一页纸速查卡）

### 能做（核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 数据/文件/URL 输入解析 | 接受用户提供的原始数据、本地文件路径或远程 URL，自动识别内容类型 |
| 2 | 关键信息提取与保留 | 从输入中提取数值序列、时间戳、标签等绘图必要字段，不丢失原始语义 |
| 3 | 结构化输出生成 | 按约定格式输出可直接用于 glowstick 渲染的图表描述（JSON/YAML） |
| 4 | 置信度标注 | 对解析结果中不确定的字段（如缺失表头、类型模糊）显式标注置信度 |
| 5 | 批量处理与自定义格式 | 支持多组数据一次性转换，允许用户指定输出字段映射规则 |

### 不能做（明确限制）

- 不执行实际的 OpenGL 渲染（需用户自行运行 glowstick 命令）
- 不处理二进制图像文件（如 PNG/JPG 中的图表）
- 不推断超出输入范围的数据趋势或预测
- 不修改用户原始数据文件（只读解析）

### 适用对象

- 需要在 Ruby 环境中快速预览数据的开发者
- 需要将 CSV/JSON/日志文件转为实时图表的运维人员
- 需要从 URL 拉取数据并可视化的数据分析师


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

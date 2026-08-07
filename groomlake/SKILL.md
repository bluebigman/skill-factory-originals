---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: groomlake
name: groomlake
displayName: 文件解析 格式转换 数据提取
description: 解析Adobe系列文件格式，提取关键信息并转换为结构化数据。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/groomlake
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 格式工坊
agent_created: true
trigger_words: ["groomlake", "Adobe文件解析", "格式转换", "数据提取", "文件解析"]
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

# groomlake — Adobe 文件格式解析与数据提取

## 一、能力边界速查卡

### 1.1 能做什么

| 序号 | 能力项 | 说明 | 适用场景 |
|------|--------|------|----------|
| 1 | 文件格式识别 | 自动检测输入文件属于哪种 Adobe 格式（如 PSD、AI、PDF 等） | 用户上传未知格式文件时 |
| 2 | 关键信息提取 | 从文件中提取元数据、图层信息、颜色模式、尺寸等核心字段 | 需要快速了解文件属性时 |
| 3 | 结构化输出 | 将解析结果整理为 JSON/YAML 等结构化格式 | 需要程序化处理解析结果时 |
| 4 | 批量处理 | 支持同时解析多个文件，输出汇总结果 | 需要批量检查文件时 |
| 5 | 置信度标注 | 对每个提取字段标注置信度等级（高/中/低） | 需要评估解析结果可靠性时 |

### 1.2 不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不修改原文件 | 本工具只读解析，不提供文件编辑功能 |
| 2 | 不支持加密文件 | 密码保护的文件无法解析 |
| 3 | 不处理损坏文件 | 文件头损坏或结构异常时无法解析 |
| 4 | 不识别所有 Adobe 格式 | 仅支持已定义格式列表（见 1.3） |
| 5 | 不保证字段完整性 | 部分文件可能缺少某些元数据字段 |

### 1.3 支持的文件格式

| 格式 | 扩展名 | 解析深度 |
|------|--------|----------|
| Photoshop | .psd, .psb | 基础元数据 + 图层结构 |
| Illustrator | .ai | 基础元数据 + 画板信息 |
| PDF | .pdf | 基础元数据 + 页面信息 |
| InDesign | .indd | 基础元数据（部分支持） |
| After Effects | .aep | 基础元数据（部分支持） |


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

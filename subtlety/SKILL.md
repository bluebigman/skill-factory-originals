---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: subtlety
name: subtlety
displayName: 数据格式转换 信息提取 结构化输出
description: 将SVN、RSS、hAtom等数据源转换为Atom或结构化格式，支持批量处理与置信度标注。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/subtlety
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Studio
agent_created: true
trigger_words: ["subtlety", "SVN转RSS", "hAtom转Atom", "格式转换", "数据源转换", "RSS生成", "Atom生成"]
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

# Subtlety — 数据源格式转换与结构化输出 Skill

## 一、能力边界速查卡

### ✅ 能做（核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| 1 | **数据源解析** | 支持从用户提供的文件路径、URL 或直接粘贴的文本中读取数据 |
| 2 | **格式转换** | 将 SVN 日志、RSS 2.0、hAtom 微格式等转换为 Atom 1.0 或结构化 JSON |
| 3 | **关键信息保留** | 自动识别并保留标题、作者、时间戳、链接、内容摘要等核心字段 |
| 4 | **置信度标注** | 对转换过程中存在不确定性的字段，输出 `[需核实:字段名]` 占位符 |
| 5 | **批量处理** | 支持一次传入多个数据源，按统一规则批量转换并输出汇总结果 |

### ❌ 不能做（明确边界）

- 不能访问未授权的私有网络资源（需用户提供可访问的 URL 或文件内容）
- 不能解析加密或二进制格式的 SVN 仓库（仅支持文本格式的日志输出）
- 不能自动判断输入数据的语义正确性（仅做格式转换，不做内容审核）
- 不能保证转换后的数据与原始数据在语义上完全等价（复杂嵌套结构可能丢失）

### 🎯 适用对象

| 适用场景 | 不适用场景 |
|----------|------------|
| 个人博客从 SVN 迁移到静态站点生成器 | 实时流式数据管道 |
| 将旧版 RSS 订阅源升级为 Atom 格式 | 需要双向同步的持续集成流程 |
| 从 HTML 页面提取 hAtom 微格式数据 | 需要自然语言理解的复杂内容分析 |
| 批量整理多个数据源的条目信息 | 二进制文件或多媒体资源的转换 |


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

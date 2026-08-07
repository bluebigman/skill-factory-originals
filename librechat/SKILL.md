---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: librechat
name: librechat
displayName: 数据整理 结构化输出 格式转换
description: 将任意数据、文件或链接整理为结构化、可校验的规范输出。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/librechat
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨
agent_created: true
trigger_words: ["librechat", "数据整理", "结构化输出", "格式转换", "信息提取", "数据清洗", "字段映射"]
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

# librechat — 数据整理与结构化输出 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入示例 | 输出示例 |
|--------|------|----------|----------|
| 数据整理 | 将杂乱文本、表格、日志整理为统一结构 | 多行日志、混合格式记录 | 按字段分列的 Markdown 表格 |
| 结构化输出 | 将自由文本映射到预定义字段 | 一段人物介绍 | `{ "name": "...", "age": 25 }` |
| 格式转换 | 在 JSON / YAML / CSV / Markdown 表格之间互转 | CSV 文件内容 | JSON 数组 |
| 信息提取 | 从长文中抽取关键实体与关系 | 合同条款文本 | 提取出的条款编号、日期、金额 |
| 链接解析 | 从 URL 中提取页面标题、关键元数据 | `https://example.com/article` | 标题、发布时间、作者（若可获取） |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不访问外部网络 | 仅处理用户提供的文本内容，不主动抓取网页 |
| 不执行代码 | 不运行 Python/Shell 等脚本，仅做文本转换 |
| 不保证语义理解 | 对模糊、歧义、缺失信息不强行补全，输出占位符 |
| 不处理二进制文件 | 仅支持文本格式（txt/md/csv/json/yaml） |
| 不存储用户数据 | 所有处理在会话内完成，不持久化 |

### 1.3 适用对象

- 需要将零散记录整理为表格的运营人员
- 需要将接口返回数据转为可读格式的开发者
- 需要从文档中抽取关键字段的行政/法务人员
- 任何需要快速将非结构化文本转为结构化数据的场景


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: awsome-cash
name: awsome-cash
displayName: 数据解析 结构化提取 置信度标注
description: 将任意数据、文件或URL解析为结构化结果，并标注置信度。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/awsome-cash
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingDataWorks
agent_created: true
trigger_words: ["代码审查", "数据解析", "结构化输出", "信息提取", "格式转换", "数据清洗", "字段映射"]

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

# awsome-cash — 数据解析与结构化提取工具

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入示例 | 输出示例 |
|--------|------|----------|----------|
| 文本解析 | 从纯文本中提取关键字段 | 一段包含姓名、日期、金额的文本 | `{"name":"张三","date":"2024-03-15","amount":1280.50}` |
| 文件解析 | 支持 CSV、JSON、TXT、Markdown 文件 | 上传 CSV 文件 | 结构化 JSON 数组 |
| URL 内容提取 | 从网页中提取正文与元数据 | 提供网页链接 | 标题、正文摘要、关键实体 |
| 格式转换 | 在 JSON / CSV / YAML 之间互转 | JSON 字符串 | CSV 表格 |
| 代码审查辅助 | 从代码中提取函数签名、依赖、TODO 标记 | 代码片段 | 结构化清单 |

### 1.2 不能做什么

- **不执行代码**：仅做静态文本分析，不运行程序、不访问数据库。
- **不处理二进制文件**：仅支持文本类文件（`.txt`, `.csv`, `.json`, `.md`, `.yaml`, `.log`）。
- **不进行语义推理**：不判断文本的"真实含义"，只做模式匹配与字段映射。
- **不保证字段完整性**：源数据缺失时，输出 `[需核实:字段名]` 占位符，不猜测填充。

### 1.3 适用对象

- 需要快速将非结构化文本转为表格/JSON 的数据分析师
- 需要批量提取网页信息的调研人员
- 需要将日志文件转为结构化记录的运维工程师
- 需要从代码中提取元信息的开发者


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

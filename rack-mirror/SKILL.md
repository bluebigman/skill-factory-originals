---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: rack-mirror
name: rack-mirror
displayName: 数据镜像 结构化转换 信息提取
description: 将用户输入的数据、文件或URL转换为结构化结果，保留关键信息并标注置信度。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/rack-mirror
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 墨规
agent_created: true
trigger_words: ["rack-mirror", "rack mirror", "数据镜像", "结构化转换", "信息提取", "内容解析"]
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

# rack-mirror Skill 文档

## 一、能力边界速查卡

本 Skill 提供数据镜像与结构化转换能力，将用户提供的原始内容（文本、文件路径、URL）解析为约定格式的结构化结果。

| 维度 | 说明 |
|------|------|
| **输入来源** | 用户直接粘贴的文本、本地文件路径、可访问的 URL |
| **输出格式** | JSON 结构化对象，含 `content`、`meta`、`confidence` 三个顶层字段 |
| **核心能力** | ① 内容解析 ② 关键信息识别 ③ 格式转换 ④ 置信度标注 ⑤ 批量处理 |
| **处理上限** | 单次输入不超过 5000 字符；批量处理不超过 20 条 |
| **处理耗时** | 单条平均 1-3 秒，批量不超过 30 秒 |

### 能做与不能做

**能做：**

- 从纯文本中提取人名、日期、金额、地址、编号等实体信息
- 将 Markdown、HTML 片段转换为纯文本并提取标题层级
- 识别 URL 指向页面的标题、描述、关键词（需网络可达）
- 对提取结果逐字段标注置信度（高/中/低）
- 按用户指定模板（JSON Schema）重组输出结构

**不能做：**

- 不能访问需要登录认证的页面或文件
- 不能解析超过 5000 字符的输入（超出部分截断并提示）
- 不能保证 OCR 级别的图片文字识别（仅支持纯文本输入）
- 不能对提取结果进行语义推理或情感分析
- 不能处理加密文件或二进制格式

**适用对象：**

- 需要快速将非结构化文本转为结构化数据的内容运营人员
- 需要批量提取网页关键信息的研究人员
- 需要统一数据格式的接口对接开发者


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: rack-mirror
name: rack-mirror
displayName: 数据镜像 结构化转换 信息提取
description: 将输入数据、文件或URL转换为结构化结果，保留关键信息并标注置信度。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/rack-mirror
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingDataWorks
agent_created: true
trigger_words: ["rack-mirror", "rack mirror", "数据镜像", "结构化转换", "信息提取", "数据映射", "字段抽取"]

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

# rack-mirror Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入示例 | 输出示例 |
|--------|------|----------|----------|
| 文本数据镜像 | 将非结构化文本转为结构化字段 | `"张三，电话13800138000，邮箱zhang@example.com"` | `{"姓名":"张三","电话":"13800138000","邮箱":"zhang@example.com","置信度":0.95}` |
| 文件内容提取 | 从纯文本文件（.txt/.md/.csv）中抽取关键字段 | 日志文件、配置文档 | 结构化 JSON 对象 |
| URL 内容解析 | 抓取公开网页正文并提取关键信息 | `https://example.com/product/123` | 商品名称、价格、描述等字段 |
| 字段置信度标注 | 每个提取字段附带置信度分数（0-1） | 任意输入 | `{"字段名":"值","_confidence":{"字段名":0.92}}` |
| 批量处理 | 一次输入多条记录，逐条结构化输出 | 多行文本 | 数组形式的 JSON 输出 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不支持二进制文件解析 | 图片、PDF、Word 等二进制格式需先转文本 |
| 不执行代码或脚本 | 输入中的代码片段仅作为文本处理 |
| 不访问需登录的页面 | 仅处理公开可访问的 URL |
| 不进行语义推理 | 仅做模式匹配和字段抽取，不做情感分析或意图判断 |
| 不保证字段完整性 | 缺失字段以 `[需核实:字段名]` 占位，不编造内容 |

### 1.3 适用对象

- **适用**：需要快速将散乱文本转为结构化数据的开发者、数据分析师、运维人员
- **不适用**：需要深度语义理解、跨文档关联推理、或对提取准确性有严格法律/财务要求的场景


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

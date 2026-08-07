---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ok
name: ok
displayName: 数据整理 结构化输出 置信度标注
description: 将任意数据、文件或URL转为结构化结果，并标注置信度。
version: 1.0.3
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ok
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨研
agent_created: true
trigger_words: ["代码审查", "数据整理", "结构化输出", "信息提取", "格式转换", "数据清洗", "内容解析"]
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

# Skill: ok — 通用数据整理与结构化输出工具

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入示例 | 输出示例 |
|--------|------|----------|----------|
| 数据整理 | 将散乱文本、表格、日志整理为统一结构 | 多行日志、CSV片段 | 结构化JSON数组 |
| 信息提取 | 从非结构化文本中抽取关键字段 | 一段新闻、邮件正文 | 字段-值映射表 |
| 格式转换 | 在JSON/YAML/CSV/纯文本间互相转换 | JSON对象 | YAML文本 |
| URL内容解析 | 抓取并解析公开网页内容 | https://example.com | 标题+正文摘要+链接列表 |
| 代码审查辅助 | 对代码片段做静态结构分析 | Python函数代码 | 函数签名+复杂度+风险点 |
| 置信度标注 | 对每个输出字段标注可信程度 | 任意输入 | 带confidence字段的结果 |

### 1.2 不能做什么（明确拒绝）

- 不能访问需要登录认证的私有系统
- 不能执行代码或运行程序
- 不能修改原始文件（只输出处理结果）
- 不能保证提取信息的绝对正确性（会标注置信度）
- 不能处理超过10MB的单个文件（建议先拆分）
- 不能识别图片中的文字（OCR不在本Skill范围内）

### 1.3 适用对象

- 需要快速整理数据的开发者
- 需要批量处理文本文件的运维人员
- 需要从网页提取信息的研究者
- 需要统一格式输出的自动化流程调用方


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

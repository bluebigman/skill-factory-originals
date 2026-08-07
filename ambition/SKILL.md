---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ambition
name: ambition
displayName: 数据解析 结构化输出 置信度标注
description: 将用户提供的数据、文件或URL转换为结构化结果，识别关键信息并按约定格式输出。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ambition
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林默
agent_created: true
trigger_words: ["ambition", "数据解析", "结构化输出", "信息提取", "格式转换"]

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

# ambition — 数据解析与结构化输出 Skill

## 一、能力边界速查卡

### ✅ 能做（5项核心能力）

| 编号 | 能力 | 说明 |
|------|------|------|
| 1 | 多源输入解析 | 接受用户直接粘贴的文本、上传的文件（CSV/JSON/TXT/MD）、或可访问的URL内容 |
| 2 | 关键信息识别 | 从非结构化或半结构化内容中抽取实体、字段、数值、日期等关键要素 |
| 3 | 约定格式输出 | 按用户指定的字段结构或默认模板生成规范化结果（JSON/Markdown表格/纯文本） |
| 4 | 置信度标注 | 对每个输出字段附加置信度等级（高/中/低），低置信度时明确提示 |
| 5 | 批量与自定义 | 支持多条记录批量处理；支持用户自定义输出字段名和排序规则 |

### ❌ 不能做（明确边界）

- 不能访问需要登录认证的私有系统或API
- 不能对加密文件或二进制格式（如图片、PDF扫描件）进行内容解析
- 不能保证解析结果的绝对正确性——所有输出均基于输入内容的可读信息
- 不能自动执行下载、上传或任何网络写操作
- 不能处理超过单次 500KB 的文本输入（超出部分需分批提交）

### 🎯 适用对象

- 需要将零散数据整理为表格/JSON 的运营人员
- 需要从网页或文档中批量提取字段的研究人员
- 需要统一数据格式以便入库的开发者
- 任何有"给我把这段内容整理成结构化格式"需求的用户


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

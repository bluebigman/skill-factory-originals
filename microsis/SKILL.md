---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: microsis
name: microsis
displayName: 旧档解析 字段还原 置信标注
description: 将老旧数据、文件或URL解析为结构化结果，保留关键信息并标注置信度。
version: 1.0.4
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/microsis
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: skill-forge-lab
agent_created: true
trigger_words: ["microsis", "旧数据解析", "结构化提取", "字段还原", "老旧文件转换", "数据清洗", "历史档案数字化"]
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

# microsis — 旧档解析与结构化提取 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入示例 | 输出示例 |
|--------|------|----------|----------|
| 老旧文本解析 | 从非结构化文本中提取关键字段 | `"张三，男，1985年生，北京"` | `{"name":"张三","gender":"男","birth_year":1985,"city":"北京"}` |
| 文件内容提取 | 解析 .txt/.csv/.log/.json 等常见格式 | 日志文件路径 | 结构化 JSON 数组 |
| URL 内容解析 | 抓取网页正文并提取元信息 | `https://example.com/old-page` | `{"title":"...","meta":{...},"content_snippet":"..."}` |
| 字段还原 | 将扁平数据还原为嵌套结构 | `user.name=张三&user.age=38` | `{"user":{"name":"张三","age":38}}` |
| 置信度标注 | 对每个提取字段给出可信度评分 | 任意输入 | `{"field":"name","value":"张三","confidence":0.95}` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不处理二进制格式 | 如 PDF 内嵌图片、扫描件 OCR 不在本 Skill 范围内 |
| 不执行代码 | 不会运行输入中的脚本或可执行文件 |
| 不保证字段完整性 | 源数据缺失时，输出 `[需核实:字段名]` 占位符，不猜测 |
| 不处理加密内容 | 加密压缩包、密码保护文件直接报错 |
| 不进行语义推理 | 只做模式匹配与结构还原，不做情感分析或意图判断 |

### 1.3 适用对象

- 需要批量整理历史文本档案的运营人员
- 需要从旧系统中迁移数据的开发人员
- 需要快速了解老旧 URL 页面内容的信息收集者
- 需要将非标准格式转为标准 JSON 的数据工程师


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

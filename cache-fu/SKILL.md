---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: cache-fu
name: cache-fu
displayName: 数据缓存 结构化解析 信息提取
description: 将任意输入数据解析为结构化结果，保留关键信息并标注置信度。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/cache-fu
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["cache fu", "缓存处理", "数据解析", "结构化输出", "信息提取", "数据整理"]
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

# cache-fu Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入类型 | 用户直接粘贴的文本、上传的文件内容、可访问的 URL 指向的文本数据 | 二进制文件（图片/视频/音频）、需要登录鉴权的私有数据源 |
| 处理动作 | 解析文本结构、识别关键字段、按模板重组输出、批量处理多条记录 | 修改原始数据源、执行网络请求以外的系统操作、跨语言翻译 |
| 输出形式 | 结构化文本（JSON/CSV/表格）、带置信度标注的字段清单 | 直接写入用户本地文件系统（需用户自行保存） |
| 自定义能力 | 接受用户指定的字段模板、分隔符、输出格式偏好 | 在用户未明确要求时擅自改变输出结构 |
| 错误处理 | 对缺失字段标注 `[需核实:字段名]`、对模糊信息给出置信度提示 | 编造不存在的值、猜测用户未提供的信息 |

### 1.2 适用对象

- 需要快速从零散文本中提取结构化信息的用户
- 需要批量整理 URL 或文件内容为统一格式的用户
- 需要将非标准数据转换为可导入其他工具格式的用户


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

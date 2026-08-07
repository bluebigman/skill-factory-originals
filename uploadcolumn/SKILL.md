---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: uploadcolumn
name: uploadcolumn
displayName: 数据上载 字段解析 结构转换
description: 将用户提供的文件或链接解析为结构化字段结果，支持批量与置信度标注。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/uploadcolumn
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 墨守规
agent_created: true
trigger_words: ["uploadcolumn", "上载列", "字段解析", "数据转换", "结构化输出"]
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

# UploadColumn 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做清单

| 序号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 数据/文件/URL 解析 | 接受用户提供的原始数据、文件路径或网络链接，提取其中关键字段 |
| 2 | 关键信息识别与保留 | 自动识别输入中的核心字段（如名称、日期、编号、金额等），保留原始语义 |
| 3 | 约定格式输出 | 按用户指定的字段结构或默认模板生成结构化结果（JSON/CSV/Markdown 表格） |
| 4 | 置信度标注 | 对每个输出字段标注可信程度（高/中/低），不确定项明确提示 |
| 5 | 批量处理与自定义格式 | 支持多文件/多记录批量转换，允许用户自定义输出模板 |

### 1.2 不能做清单

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行数据清洗 | 不自动修正输入中的错别字、乱码或格式错误，仅原样提取 |
| 2 | 不推断缺失值 | 输入中不存在的字段，输出为 `[需核实:字段名]`，不做猜测填充 |
| 3 | 不处理加密/权限文件 | 无法读取受密码保护或权限受限的文件 |
| 4 | 不保证字段完整性 | 若输入本身缺少关键信息，输出中对应字段留空并标注 |
| 5 | 不进行语义翻译 | 不将非中文内容翻译为中文，仅按原语言提取 |

### 1.3 适用对象

- 需要将非结构化数据（文本、表格截图、URL 内容）转为结构化记录的人员
- 需要批量整理文件清单、数据台账的运营或行政岗位
- 需要快速提取网页或文档中关键字段的研究人员


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

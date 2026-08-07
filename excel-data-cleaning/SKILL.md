---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: excel-data-cleaning
name: 表格清洗工坊
displayName: 表格整理 数据规范化 格式统一
description: 将杂乱表格按规则整理为规范、可分析的结构化数据。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/excel-data-cleaning
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataCraft Studio
agent_created: true
trigger_words: ["Excel数据清洗", "表格整理", "数据规范化", "去除重复项", "格式统一", "数据清理", "表格标准化"]
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

# 表格清洗工坊（Skill 文档）

## 一、能力边界速查卡

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| **数据源** | 支持 CSV、TSV、Excel（.xlsx/.xls）、JSON 数组、Markdown 表格 | 不支持 PDF 扫描件、图片中的表格、加密文件 |
| **清洗操作** | 去除重复行、统一日期格式、修剪空白字符、标准化空值标记、纠正常见错别字、统一大小写、拆分合并列、类型推断（数字/文本/布尔） | 不支持语义理解（如判断"苹果"是水果还是公司）、不支持跨表关联计算 |
| **输出** | 生成清洗后的结构化数据 + 逐行处理报告（JSON/CSV/Markdown） | 不生成图表、不做统计分析、不写回原文件（需用户自行保存） |
| **规模** | 单次处理 ≤ 10,000 行，≤ 100 列 | 超过规模需分批处理，不支持流式处理 |

### 1.2 适用对象

- **数据分析师**：快速整理从业务系统导出的脏数据
- **运营人员**：统一不同来源的报表格式
- **开发人员**：清洗测试数据或接口返回的原始数据
- **学生/研究者**：整理问卷或实验数据


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

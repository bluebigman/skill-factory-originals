---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: invoice-data-extraction-system
name: invoice-data-extraction-system
displayName: 票据解析 信息抽取 结构化输出
description: 将发票PDF或图片转为结构化数据，含置信度标注与批量处理。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/invoice-data-extraction-system
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据工坊
agent_created: true
trigger_words: ["发票识别", "票据解析", "invoice data extraction", "发票信息抽取", "OCR结构化", "票据信息录入", "发票数据化"]
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

# 票据解析与结构化抽取系统

## 一、能力边界（一页纸速查卡）

### 1.1 系统能做什么

| 能力项 | 说明 | 输入要求 |
|--------|------|----------|
| 单张识别 | 从一张发票图片/PDF中提取关键字段 | 清晰可读的扫描件或电子发票 |
| 批量处理 | 一次处理多张票据，输出汇总表 | 文件夹路径或文件列表 |
| 置信度标注 | 每个字段附带可信度评分（0-1） | 自动计算，无需人工干预 |
| 格式归一 | 日期、金额、税号等字段统一格式 | 自动完成 |
| 结果导出 | 输出为 JSON / CSV / Excel | 用户指定格式 |

### 1.2 系统不能做什么

- 不能识别手写模糊、严重倾斜、反光遮挡的票据
- 不能处理非发票类文档（如合同、收据、订单）
- 不能验证发票真伪（需对接税务系统）
- 不能自动修正原始数据错误（仅标注置信度）
- 不能处理加密或损坏的 PDF 文件

### 1.3 适用对象

- 财务人员：日常报销单录入
- 审计人员：批量核查票据信息
- 开发人员：对接业务系统的数据管道
- 行政人员：差旅票据归档整理


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agency-agents
name: agency-agency-agents
displayName: 数字代理 任务编排 多角色协作
description: 将输入数据转化为结构化结果，支持批量处理与自定义格式输出。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agency-agents
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["agency-agents", "数据转换", "结构化输出", "批量处理", "信息提取"]
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

# 数字代理 任务编排 多角色协作

## 一、能力边界速查卡

### 1.1 能做什么

| 编号 | 能力项 | 说明 | 输入示例 | 输出示例 |
|------|--------|------|----------|----------|
| C1 | 数据/文件/URL 转结构化结果 | 解析文本、PDF、网页链接，提取关键字段 | 一段产品描述文本 | JSON 对象含名称、价格、规格 |
| C2 | 关键信息识别与保留 | 自动识别实体、数字、日期、专有名词 | 会议纪要文本 | 结构化会议记录含时间、决策项 |
| C3 | 按约定格式生成输出 | 支持 JSON、CSV、Markdown 表格、自定义模板 | 原始数据 + 格式要求 | 符合模板的文档 |
| C4 | 置信度标注 | 对每个输出字段标注可信程度（高/中/低） | 模糊信息输入 | 字段附带 confidence 属性 |
| C5 | 批量处理与自定义格式 | 一次处理多条记录，支持用户自定义字段映射 | 100 条客户反馈 | 按指定字段汇总的表格 |

### 1.2 不能做什么

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行外部操作 | 不发送邮件、不调用第三方 API、不修改文件系统 |
| L2 | 不进行主观判断 | 不提供建议、不评估好坏、不预测趋势 |
| L3 | 不处理无文本内容 | 纯图片、纯音频、纯视频无法直接解析（需先转文字） |
| L4 | 不保证数据准确性 | 输入数据本身有误时，输出同样有误，仅做格式转换 |
| L5 | 不处理超大规模数据 | 单次处理上限：文本 10 万字符，文件 5MB，URL 20 个 |

### 1.3 适用对象

- **内容运营人员**：将用户反馈、评论批量转为结构化表格
- **数据分析师**：从非结构化文本中提取指标字段
- **产品经理**：将竞品页面信息整理为对比清单
- **行政人员**：将会议记录、通知转为标准格式文档


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

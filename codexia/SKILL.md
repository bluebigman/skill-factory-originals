---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: codexia
name: codexia
displayName: 数据解析 结构化转换 批处理
description: 将用户提供的任意数据转换为结构化结果，支持批量处理与置信度标注。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/codexia
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 技能工坊
agent_created: true
trigger_words: ["codexia", "数据解析", "结构化转换", "批量处理", "信息提取"]
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

# codexia 技能文档

## 一、能力边界（一页纸速查卡）

### 能做（5项核心能力）

| 序号 | 能力项 | 说明 | 典型场景 |
|------|--------|------|----------|
| 1 | 数据转结构化 | 将用户提供的原始数据（文本/文件/URL）转换为 JSON 或表格结构 | 从网页抓取商品信息并整理为表格 |
| 2 | 关键信息识别 | 自动提取输入中的关键字段（如名称、日期、金额、编号） | 从合同文本中提取签约双方与金额 |
| 3 | 约定格式输出 | 按用户指定的字段结构或模板生成输出 | 按固定模板生成周报数据 |
| 4 | 置信度标注 | 对不确定的字段标注置信度等级（高/中/低） | 识别手写扫描件时标注低置信度字段 |
| 5 | 批量处理 | 支持多文件、多 URL、多条目的一次性处理 | 批量解析 100 条客户反馈 |

### 不能做（明确边界）

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行代码 | 本技能仅做数据解析与转换，不运行或执行任何代码逻辑 |
| 2 | 不访问私有数据 | 无法访问需要登录认证的网站或加密文件 |
| 3 | 不保证绝对准确 | 对模糊输入或缺失字段，输出会标注置信度而非强行补全 |
| 4 | 不处理非文本内容 | 图片、音频、视频等非文本格式需先转换为文本 |
| 5 | 不提供法律/财务建议 | 解析结果仅供参考，不构成专业意见 |

### 适用对象

- 需要快速整理数据的运营人员
- 需要批量提取信息的开发者
- 需要将非结构化数据转为结构化格式的普通用户


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: webbot
name: webbot
displayName: 网页采集 数据提取 结构化处理
description: 将网页或文件内容转化为结构化数据，支持批量处理与置信度标注。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/webbot
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨
agent_created: true
trigger_words: ["爬虫采集", "网页抓取", "数据提取", "结构化输出", "webbot"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# webbot — 网页采集与结构化输出 Skill 文档

## 一、能力边界（一页纸速查卡）

### 能做（5 项核心能力）

| 编号 | 能力项 | 说明 | 示例 |
|------|--------|------|------|
| 1 | 数据/文件/URL → 结构化结果 | 将用户提供的任意来源内容转换为 JSON/CSV 等结构化格式 | 从商品页面提取名称、价格、库存 |
| 2 | 关键信息识别与保留 | 自动识别输入中的核心字段，保留上下文关联信息 | 识别文章标题、作者、发布时间 |
| 3 | 按约定格式生成输出 | 遵循用户指定的字段结构或默认模板输出 | 输出 `{title, url, date}` 格式 |
| 4 | 置信度提示 | 对不确定的字段标注置信度等级（高/中/低） | `"price": 199.00, "confidence": 0.92` |
| 5 | 批量处理与自定义格式 | 支持多 URL/多文件批量处理，可自定义输出模板 | 一次处理 50 个商品链接，输出 Excel 兼容 CSV |

### 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 绕过登录/验证码 | 不提供任何绕过访问控制的手段 |
| 2 | 高频请求 | 单次任务请求间隔不低于 2 秒，不提供并发加速 |
| 3 | 动态渲染页面（默认） | 默认仅处理静态 HTML；如需 JS 渲染需用户明确说明 |
| 4 | 数据清洗保证 | 不保证提取数据的业务准确性，仅做格式结构化 |
| 5 | 存储服务 | 不提供数据持久化存储，仅返回结果 |

### 适用对象

- 需要将网页内容转为表格/JSON 的开发者
- 需要批量提取公开页面信息的研究人员
- 需要快速验证页面结构的测试人员


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: pbottlerpa
name: pbottlerpa
displayName: 网页流程自动化 数据抓取 效率提升
description: 面向专业用户的RPA+AI流程自动化工具，支持网页操作与数据提取。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/pbottlerpa
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Studio
agent_created: true
trigger_words: ["pbottlerpa", "RPA", "流程自动化", "网页自动化", "数据抓取", "自动化脚本", "网页数据采集"]
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

# pbottlerpa — 网页流程自动化与数据抓取 Skill 文档

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 能力类别 | 具体功能 | 典型场景 |
|---------|---------|---------|
| 网页操作 | 自动点击、填表、翻页、滚动、悬停 | 表单批量提交、分页遍历 |
| 数据提取 | 结构化字段抓取、表格导出、文本抽取 | 商品价格监控、新闻标题汇总 |
| 流程编排 | 多步骤串联、条件分支、循环执行 | 每日定时巡检、批量数据同步 |
| 结果输出 | JSON/CSV 导出、日志记录、截图留档 | 数据交接、审计追溯 |

### 1.2 不能做什么

| 限制项 | 说明 |
|-------|------|
| 不处理验证码 | 若页面出现验证码，流程将暂停并提示人工介入 |
| 不绕过登录/权限 | 仅操作已授权访问的页面，不做凭证绕过 |
| 不执行 JS 逆向 | 对动态渲染内容仅支持标准 DOM 操作 |
| 不保证页面兼容 | 对非标准 HTML 或极端反爬策略的站点，可能失败 |

### 1.3 适用对象

- 需要重复性网页操作的运营人员
- 需要定期采集公开数据的分析师
- 需要将网页流程嵌入自动化管线的开发者


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

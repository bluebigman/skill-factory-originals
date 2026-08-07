---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: scrapecraft
name: scrapecraft
displayName: 网页采集 可视化流程 数据抽取
description: 用自然语言构建、测试并部署网页采集流程的可视化编辑器。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/scrapecraft
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Studio
agent_created: true
trigger_words: ["爬虫采集", "网页抓取", "数据抽取", "采集流程", "scrapecraft"]
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

# Scrapecraft — 网页采集流程设计助手

## 一、能力边界速查卡

### 本 Skill 能做什么

| 序号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| 1 | 自然语言转采集流程 | 将口语化描述转换为结构化采集步骤 | "抓取某电商网站的商品标题和价格" |
| 2 | 结构化数据输出 | 将网页内容整理为 JSON/CSV 等格式 | 商品列表 → `[{title, price}]` |
| 3 | 关键字段识别 | 自动识别输入中的核心数据要素 | 从 URL 中识别域名、路径参数 |
| 4 | 批量任务拆分 | 将多页/多列表采集拆分为可执行步骤 | 翻页规则、循环采集逻辑 |
| 5 | 流程自检与修正 | 检查字段完整性并给出修正建议 | 缺失字段 → 提示补充选择器 |

### 本 Skill 不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行实际抓取 | 仅生成流程设计，不发起网络请求 |
| 2 | 不处理反爬策略 | 不涉及验证码破解、IP 代理等对抗手段 |
| 3 | 不保证数据准确性 | 目标网站结构变化可能导致选择器失效 |
| 4 | 不存储用户数据 | 所有处理均在会话内完成 |

### 适用对象

- 需要快速搭建采集流程的产品经理
- 需要将采集需求文档化的开发人员
- 需要评估采集可行性的数据分析师


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

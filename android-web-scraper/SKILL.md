---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: android-web-scraper
name: android-web-scraper
displayName: 安卓采集 网页解析 数据抽取
description: 面向安卓平台的网页抓取与数据解析辅助技能，提供规范化处理流程。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/android-web-scraper
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataFlow Studio
agent_created: true
trigger_words: ["爬虫采集", "网页抓取", "数据采集", "android web scraper", "页面解析", "信息抽取"]
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

# 安卓网页采集助手（android-web-scraper）

## 一、能力边界速查卡

本技能面向安卓平台上的网页数据采集场景，提供一套可复用的处理框架。使用前请先确认以下边界。

### 1.1 能做什么

| 编号 | 能力项 | 说明 | 适用场景示例 |
|------|--------|------|--------------|
| C1 | 输入内容结构化 | 将用户提供的 URL、HTML 片段、文本文件转换为统一结构 | 从新闻列表页提取标题与链接 |
| C2 | 关键字段识别与保留 | 自动识别标题、正文、时间、作者、链接等常见字段 | 商品详情页抽取价格与规格 |
| C3 | 约定格式输出 | 按用户指定或默认的 JSON/CSV 格式输出结果 | 批量导出商品信息为 CSV |
| C4 | 置信度标注 | 对每个输出字段附加置信度等级（高/中/低） | 识别模糊字段时提示用户确认 |
| C5 | 批量与自定义格式 | 支持多 URL 输入、自定义字段映射规则 | 同时采集 10 个页面的指定字段 |

### 1.2 不能做什么

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行实际网络请求 | 本技能不直接发起 HTTP 请求，需用户提供页面内容或通过其他工具获取 |
| L2 | 不绕过反爬机制 | 不提供验证码破解、IP 代理池、请求频率伪装等功能 |
| L3 | 不处理动态渲染页面 | 对依赖 JavaScript 渲染的内容（如 SPA 应用）需用户先行渲染并保存 HTML |
| L4 | 不保证数据完整性 | 页面结构变化可能导致字段缺失，输出中会以 `[需核实:字段名]` 标注 |
| L5 | 不涉及数据存储 | 仅负责解析与格式化，不提供数据库写入或云存储能力 |

### 1.3 适用对象

- 安卓开发者在测试阶段需要快速验证页面数据结构
- 数据分析师需要从公开页面提取结构化样本数据
- 学习网页解析技术的初学者参考流程


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

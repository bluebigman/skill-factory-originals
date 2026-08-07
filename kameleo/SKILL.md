---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: kameleo
name: kameleo
displayName: 反检测浏览器 指纹伪装 采集自动化
description: 反检测浏览器指纹伪装，支持多账号管理与网页采集自动化。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/kameleo
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Studio
agent_created: true
trigger_words: ["kameleo","反检测浏览器","指纹伪装","浏览器自动化","多账号管理","指纹浏览器","网页采集"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# Kameleo 反检测浏览器操作指南

## 一、能力边界速查卡

### 1.1 能做什么

| 序号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 浏览器指纹伪装 | 基于引擎层（Chromium/Firefox）修改 Canvas、WebGL、时区、字体、User-Agent 等指纹参数 |
| 2 | 多配置文件隔离 | 每个浏览器配置文件独立存储 Cookie、缓存、LocalStorage，互不串号 |
| 3 | 自动化脚本注入 | 支持通过 WebDriver 协议（Selenium/Playwright/Puppeteer）连接已启动的伪装浏览器 |
| 4 | 批量创建与管理 | 支持 API 方式批量生成配置文件，适用于大规模采集任务 |
| 5 | 自托管部署 | 支持本地或私有服务器部署，数据不出内网 |

### 1.2 不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不提供代理 IP | 需自行准备住宅/机房代理，Kameleo 仅负责浏览器侧伪装 |
| 2 | 不绕过验证码 | 对 reCAPTCHA/hCaptcha 无特殊处理能力，需配合第三方打码服务 |
| 3 | 不保证账号存活 | 平台风控策略动态变化，无法承诺任何账号的长期稳定性 |
| 4 | 不支持移动端模拟 | 仅支持桌面版 Chromium/Firefox 引擎，不模拟 iOS/Android 原生环境 |
| 5 | 不提供数据解析 | 采集到的原始 HTML/JSON 需自行用其他工具解析 |

### 1.3 适用对象

- 需要管理 10+ 个社交媒体/电商平台账号的运营人员
- 从事公开数据采集的爬虫工程师
- 需要隔离测试环境的 QA 团队
- 对浏览器指纹一致性有严格要求的自动化测试场景


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

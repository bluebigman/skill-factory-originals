---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: android-web-scraper
name: android-web-scraper
displayName: 安卓网页采集 后台抓取 数据提取
description: 在安卓后台静默执行网页任务，将网页内容转化为结构化数据。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/android-web-scraper
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据工坊
agent_created: true
trigger_words: ["android-web-scraper", "安卓网页抓取", "后台网页任务", "网页数据采集", "Android Web Scraper"]

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

# Android Web Scraper 技能文档

## 一、能力边界：一页纸速查卡

本技能面向需要在安卓设备后台执行网页抓取任务的开发者或自动化流程设计者。它不是一个可视化爬虫工具，而是一个库级别的能力封装，用于将网页请求、解析、结构化输出串联为可复用的后台任务。

### 1.1 能做（核心能力清单）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| C1 | 后台网页请求 | 在安卓后台线程发起 HTTP 请求，获取目标 URL 的 HTML 内容 |
| C2 | 结构化数据提取 | 从 HTML 中提取指定字段，输出为 JSON 或 CSV 格式 |
| C3 | 批量 URL 处理 | 支持传入多个 URL，按顺序或并发执行抓取任务 |
| C4 | 自定义解析规则 | 允许用户通过 CSS 选择器或 XPath 定义提取规则 |
| C5 | 结果校验与置信度标注 | 对提取结果进行完整性检查，对缺失字段标注置信度 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不处理登录态 | 不自动处理 Cookie 会话、OAuth 授权或验证码 |
| L2 | 不执行 JavaScript | 仅抓取静态 HTML，不渲染动态内容 |
| L3 | 不绕过反爬机制 | 不提供代理池、IP 轮换或指纹伪装功能 |
| L4 | 不处理二进制文件 | 不下载图片、PDF、视频等非 HTML 资源 |
| L5 | 不提供 GUI | 无图形界面，仅通过 API 或命令行参数调用 |

### 1.3 适用对象

- 需要定期采集公开网页数据的安卓应用开发者
- 需要将网页内容同步到本地数据库的自动化脚本编写者
- 对网页结构有基本了解，能编写 CSS 选择器或 XPath 的技术人员


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

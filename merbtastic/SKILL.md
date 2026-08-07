---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: merbtastic
name: merbtastic
displayName: 网站构建 动态路由 静态生成
description: 将内容源转换为 Merb+Webgen 站点，支持动态路由与静态生成。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/merbtastic
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: skill-forge-studio
agent_created: true
trigger_words: ["merbtastic", "Merb Webgen 站点生成", "动态路由配置", "静态站点生成", "Nginx 配置生成"]
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

# merbtastic — 站点构建与路由配置助手

## 一、能力边界（速查卡）

### 1.1 能做什么

| 编号 | 能力项 | 说明 | 适用对象 |
|------|--------|------|----------|
| C1 | 内容源解析 | 从用户提供的目录、文件清单或 URL 列表中提取页面结构、资源引用、元数据 | 已有内容素材，需整理为站点结构的用户 |
| C2 | 动态路由设计 | 根据内容类型生成 Merb 风格的路由规则（如 `/blog/:year/:slug`） | 需要 URL 规则可编程的站点 |
| C3 | Nginx 配置生成 | 输出反向代理、静态资源缓存、HTTPS 跳转等 Nginx 配置片段 | 需要部署到 Nginx 服务器的站点 |
| C4 | 静态站点生成 | 将 Haml/Sass/ERB 模板与内容合并，产出纯静态 HTML/CSS/JS 文件结构 | 偏好静态托管的个人或项目站点 |
| C5 | 批量处理与格式转换 | 支持多文件批量转换、模板批量应用、输出格式自定义（如 JSON 索引） | 需要定期重建或迁移的站点 |

### 1.2 不能做什么

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行部署 | 不负责将文件上传到服务器或执行远程命令 |
| L2 | 不处理动态业务逻辑 | 不生成用户登录、支付、数据库查询等后端业务代码 |
| L3 | 不保证浏览器兼容性 | 生成的 CSS/JS 需自行测试跨浏览器表现 |
| L4 | 不替代人工设计 | 视觉设计、信息架构决策需由使用者确认 |

### 1.3 输入与输出约定

- **输入来源**：用户提供的数据文件（YAML/JSON/CSV）、本地目录路径、公开 URL 列表。
- **输出格式**：默认输出为 Markdown 报告 + 生成文件清单；可指定输出为 JSON 结构或直接生成文件树。


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

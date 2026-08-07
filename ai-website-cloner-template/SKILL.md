---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ai-website-cloner-template
name: ai-website-cloner-template
displayName: 站点克隆 模板生成 结构提取
description: 将任意网站URL或文件转换为结构化克隆模板，供AI编码代理使用。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ai-website-cloner-template
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨
agent_created: true
trigger_words: ["ai website cloner template", "网站克隆", "克隆网站", "模板生成", "站点复制", "网页转模板", "站点结构提取"]
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

# 站点克隆模板生成器（ai-website-cloner-template）

## 一、能力边界速查卡

本 Skill 的核心职责：**把目标网站或本地文件解析成结构化的克隆模板**，供 AI 编码代理（如 Cursor、Copilot、自研 Agent）直接消费。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入 | 公开可访问的 URL、本地 HTML 文件、静态站点目录 | 需要登录的私有站点、动态渲染依赖 JS 的 SPA（需先预渲染） |
| 输出 | 结构化 JSON 模板（含页面骨架、组件树、样式变量、资源清单） | 直接生成可部署的完整站点代码 |
| 处理 | 提取 DOM 结构、CSS 类名、图片资源、字体引用、布局框架 | 逆向工程商业站点的后端逻辑、API 密钥、敏感数据 |
| 适配 | 响应式布局识别、常见前端框架（React/Vue/静态） | 识别自定义 Web Components 或 Shadow DOM 内部细节 |

**适用对象**：前端开发者、AI 编码工具使用者、需要快速搭建相似页面的团队、设计系统维护者。

**不适用对象**：需要像素级复刻的场合、需要抓取动态数据的场景、涉及版权争议的商业站点直接复制。


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

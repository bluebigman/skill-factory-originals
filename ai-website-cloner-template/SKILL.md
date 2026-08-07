---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ai-website-cloner-template
name: ai-website-cloner-template
displayName: 网站克隆 模板生成 一键复制
description: 将任意网站URL或文件转换为结构化克隆模板，供AI编码代理使用。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ai-website-cloner-template
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["ai website cloner template", "网站克隆", "克隆网站", "模板生成", "站点复制", "网页转模板"]
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

# AI 网站克隆模板生成器（Skill 文档）

## 一、能力边界：一页纸速查卡

本 Skill 的核心职责是：**将用户提供的网站 URL、HTML 文件或文本内容，转化为结构化的克隆模板**，供 AI 编码代理（如 Claude、DeepSeek 等）直接使用。

### ✅ 能做（5 项核心能力）

| 编号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| 1 | 解析输入源 | 支持 URL、本地 HTML 文件、纯文本三种输入来源 | `https://example.com`、`./page.html`、`一段HTML字符串` |
| 2 | 提取关键结构 | 识别页面中的标题、导航、主内容区、页脚、表单、图片等关键区块 | 从 `<nav>` 提取导航链接列表 |
| 3 | 生成结构化模板 | 输出 Markdown 格式的模板文档，包含页面结构树、组件清单、样式要点 | 输出 `template.md` |
| 4 | 置信度标注 | 对每个提取字段标注置信度（高/中/低），不确定项使用 `[需核实:字段名]` 占位 | `置信度: 高 (0.9)` |
| 5 | 批量处理 | 支持一次提交多个 URL 或文件，批量生成对应模板 | 传入 5 个 URL，输出 5 个模板文件 |

### ❌ 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行代码 | 本 Skill 只生成模板文档，不运行 JavaScript、不渲染页面 |
| 2 | 不绕过登录/付费墙 | 无法访问需要认证或付费的页面内容 |
| 3 | 不处理动态渲染内容 | 仅解析静态 HTML 或用户提供的文本，不执行浏览器渲染 |
| 4 | 不生成完整可部署代码 | 输出的是模板蓝图，而非可直接运行的完整项目 |
| 5 | 不保证像素级还原 | 模板保留结构和样式要点，但不承诺视觉完全一致 |

### 适用对象

- **AI 编码代理**：需要快速理解目标网站结构以进行仿制或重构
- **前端开发者**：作为新项目的结构参考
- **产品经理**：快速梳理竞品页面布局


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ai-website-cloner-template
name: ai-website-cloner-template
displayName: 网站克隆 页面抓取 结构还原
description: 输入网址或文件，自动解析页面结构并生成可复用的结构化模板。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ai-website-cloner-template
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 独立技能工坊
agent_created: true
trigger_words: ["网站克隆", "页面抓取", "结构还原", "网页转模板", "站点复制"]
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

# 网站克隆模板生成器（ai-website-cloner-template）

## 一、能力边界速查卡

本 Skill 面向需要将现有网站页面快速转化为结构化模板的开发人员、内容迁移团队和自动化测试工程师。它不直接下载整个站点，而是聚焦于**页面结构解析与模板生成**。

### ✅ 能做（核心能力）

| 编号 | 能力项 | 说明 | 适用场景 |
|------|--------|------|----------|
| 1 | URL 页面结构解析 | 输入一个公开可访问的 URL，提取 DOM 结构、主要区块、样式类名 | 单页分析、竞品结构参考 |
| 2 | HTML 文件解析 | 接受用户上传的 .html / .htm 文件，解析其结构 | 本地文件处理、离线分析 |
| 3 | 关键信息识别与保留 | 自动识别标题、导航、正文区、页脚、表单等关键区块，并保留其层级关系 | 页面重构、内容迁移 |
| 4 | 结构化模板输出 | 生成包含占位符的模板文件（支持 HTML / Markdown / JSON 三种格式） | 前端开发、CMS 模板制作 |
| 5 | 批量处理与自定义格式 | 支持一次提交多个 URL 或文件，并允许用户指定输出字段结构 | 批量迁移、多页面站点梳理 |

### ❌ 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行 JavaScript 渲染 | 仅解析静态 HTML，SPA（单页应用）动态渲染内容无法获取 |
| 2 | 不下载图片/视频等二进制资源 | 仅提取资源引用路径，不进行文件下载 |
| 3 | 不处理需要登录认证的页面 | 仅支持公开可访问的 URL |
| 4 | 不绕过 robots.txt 或访问限制 | 遵守目标站点的爬取规则 |
| 5 | 不生成可立即部署的完整站点 | 输出为模板骨架，需人工补充业务逻辑与样式细节 |

### 适用对象

- 前端开发者：快速获取页面布局参考
- 内容运营：批量迁移文章页面结构
- 测试工程师：生成页面结构比对基线


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

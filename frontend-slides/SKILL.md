---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: frontend-slides
name: frontend-slides
displayName: 前端幻灯片 网页演示 代码生成
description: 用前端技术将数据与内容转化为网页幻灯片，支持自定义样式与交互。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/frontend-slides
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SlideForge
agent_created: true
trigger_words: ["frontend slides", "网页幻灯片", "前端演示", "slide deck", "HTML slides"]
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

# 前端幻灯片（frontend-slides）技能文档

## 一、能力边界：一页纸速查卡

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| **输入处理** | 接受用户提供的文本数据、JSON 文件、Markdown 文档、公开 URL 中的内容 | 无法直接读取本地文件系统（需用户粘贴内容或提供可访问的 URL） |
| **内容转换** | 将结构化或半结构化内容转换为幻灯片所需的章节、要点、数据视图 | 无法理解图片中的视觉内容（除非有对应的文字描述或 alt 文本） |
| **输出生成** | 生成完整的 HTML/CSS/JS 幻灯片文件，支持多种主题风格 | 不生成 PDF、PPTX 等二进制格式（需用户自行通过浏览器打印为 PDF） |
| **交互能力** | 支持键盘导航、点击翻页、简单的动画过渡效果 | 不支持复杂的实时协作、远程控制、语音讲解 |
| **自定义扩展** | 允许用户指定配色、字体、布局偏好，支持自定义 CSS 变量 | 无法动态加载外部 JavaScript 库（需在生成时声明依赖） |

### 1.2 适用对象

- **内容创作者**：需要将博客文章、课程讲义、产品介绍快速转化为网页演示。
- **开发者**：希望用代码控制幻灯片样式，或需要将幻灯片嵌入到现有 Web 项目中。
- **教育工作者**：制作教学课件，支持在浏览器中直接展示，无需安装额外软件。

### 1.3 输入与输出规格

| 项目 | 规格 |
|------|------|
| **输入来源** | 用户直接粘贴的文本 / 上传的 .md、.json 文件内容 / 可公开访问的 URL |
| **输出文件** | 单个 `index.html` 文件（内联 CSS 与 JS），或拆分为 `index.html` + `styles.css` + `script.js` 三件套 |
| **字段结构** | 幻灯片元数据（标题、作者、日期）+ 页面数组（每页含标题、正文、备注、布局类型） |


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

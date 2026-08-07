---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: mdproof
name: mdproof
displayName: 文档排版 格式校验 PDF输出
description: 将Markdown内容转换为排版规范的PDF文件，支持批量处理与格式校验。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/mdproof
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 墨规工作室
agent_created: true
trigger_words: ["PDF转文档", "markdown转pdf", "md转pdf", "文档转换", "格式转换", "md转文档", "markdown转文档", "排版输出"]
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

# mdproof — Markdown 转 PDF 排版校验工具

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 支持程度 |
|--------|------|----------|
| 格式转换 | 将 `.md` 文件转换为 `.pdf` 文件 | ✅ 完整支持 |
| 批量处理 | 一次处理多个 Markdown 文件 | ✅ 支持（最多 50 个文件/批次） |
| 格式校验 | 检查 Markdown 语法错误、链接失效、图片路径异常 | ✅ 支持（基础级） |
| 排版规范 | 自动应用标题层级、代码块样式、表格边框、页边距 | ✅ 支持（预设模板） |
| 自定义样式 | 通过 YAML frontmatter 指定字体、字号、页边距 | ✅ 支持（有限参数） |
| 目录生成 | 自动提取标题生成 PDF 书签目录 | ✅ 支持（默认开启） |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 复杂排版 | 不支持多栏布局、浮动图片、精确像素级控制 |
| 动态内容 | 不支持 JavaScript 渲染、图表交互、表单填写 |
| 加密保护 | 不支持 PDF 密码加密、水印添加 |
| 字体嵌入 | 不支持自定义字体文件嵌入（仅使用系统字体） |
| 逆向转换 | 不支持 PDF 转回 Markdown |

### 1.3 适用对象

- 需要将技术文档、README、笔记转换为正式 PDF 的开发者
- 需要批量生成报告、手册的文档维护人员
- 需要统一排版风格的内容发布者


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

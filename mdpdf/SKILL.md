---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: mdpdf
name: mdpdf
displayName: 文档转换 PDF 样式定制 命令行工具
description: 将 Markdown 文件转换为 PDF，支持自定义样式表与自检功能。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/mdpdf
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["mdpdf", "markdown转pdf", "md转pdf", "pdf转换", "样式表转换"]
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

# mdpdf — Markdown 转 PDF 命令行工具

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| 输入格式 | 本地 `.md` 文件、标准输入（stdin）中的 Markdown 文本、指向 Markdown 文件的 URL | 二进制格式（DOCX、HTML 等）直接输入 |
| 样式控制 | 通过 CSS 样式表自定义 PDF 外观（字体、间距、页眉页脚、代码块样式） | 不支持 JavaScript 动态渲染、不支持 SVG 矢量图内嵌 |
| 输出 | 生成 PDF 文件到指定路径 | 不支持输出为 PNG/JPEG 图片格式 |
| 批量处理 | 单次命令处理单个文件；可通过脚本循环调用实现批量 | 单条命令内不支持通配符多文件输入 |
| 自检 | `--selftest` 验证环境依赖（如 wkhtmltopdf 或 Chromium）是否就绪 | 不检查 Markdown 语法正确性（语法错误会原样渲染） |
| 版本信息 | `--version` 输出当前版本号 | 无在线升级功能 |

### 1.2 适用对象

- **内容创作者**：需要将技术文档、笔记、报告转为 PDF 分享。
- **开发者**：希望在 CI/CD 流程中自动生成 PDF 文档。
- **文档维护者**：需要统一风格的 PDF 输出，通过样式表控制品牌视觉。


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

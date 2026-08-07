---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: mdpdf
name: mdpdf
displayName: 文档转换 样式定制 格式自检
description: 将 Markdown 文件转换为 PDF，支持自定义样式表与自检功能。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/mdpdf
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 独立开发者·林默
agent_created: true
trigger_words: ["mdpdf", "markdown转pdf", "md转pdf", "pdf转换", "样式表转换", "文档导出", "格式转换"]
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

# mdpdf — Markdown 转 PDF 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 基础转换 | 将 `.md` 文件转换为 `.pdf` 文件 | `mdpdf input.md` |
| 样式定制 | 通过 CSS 文件控制 PDF 排版样式 | `mdpdf input.md --style custom.css` |
| 自检功能 | 检查转换环境与依赖是否就绪 | `mdpdf --selftest` |
| 版本查询 | 显示当前工具版本号 | `mdpdf --version` |
| 批量处理 | 支持一次转换多个 Markdown 文件 | `mdpdf a.md b.md c.md` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不支持加密 PDF | 无法生成带密码保护的 PDF 文件 |
| 不支持 PDF 合并/拆分 | 仅做单向转换，不做后处理 |
| 不支持图片提取 | 转换时图片嵌入 PDF，不单独导出 |
| 不支持 OCR 识别 | 对扫描版 PDF 无处理能力 |
| 不支持实时预览 | 转换过程为命令行批处理模式 |

### 1.3 适用对象

- 需要将技术文档、README、笔记转为 PDF 的开发者
- 需要统一文档排版风格的内容维护者
- 需要在无图形界面环境下完成文档转换的用户


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

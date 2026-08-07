---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: mdproof
name: mdproof
displayName: Markdown转PDF 文档转换 格式校验
description: 将Markdown内容转换为排版规范的PDF文件，支持批量处理与格式校验。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/mdproof
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 墨规工坊
agent_created: true
trigger_words: ["PDF转文档", "markdown转pdf", "md转pdf", "文档转换", "格式转换"]
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

# mdproof — Markdown 转 PDF 转换器

## 一、能力边界速查卡

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入格式 | 标准 Markdown（.md/.markdown）、含 YAML frontmatter 的 MD 文件、URL 指向的 MD 资源 | 二进制格式（docx/xlsx）、加密文件、需登录鉴权的私有仓库文件 |
| 转换能力 | 标题层级、段落、列表（有序/无序/任务）、表格、代码块、引用块、粗斜体、行内代码、链接、图片（本地路径或公网 URL） | 复杂 LaTeX 公式渲染、Mermaid 流程图、HTML 内嵌脚本执行 |
| 输出控制 | 页面尺寸（A4/Letter）、页边距（窄/常规/宽）、字体（系统已装字体）、页眉页脚、封面页 | 自定义字体嵌入（需额外授权）、水印叠加、数字签名 |
| 批处理 | 支持多文件批量转换，输出到指定目录 | 不支持跨设备分布式转换 |
| 校验能力 | 识别未闭合代码块、非法表格分隔符、URL 格式异常 | 语义级纠错（如自动修复错别字） |

### 1.2 适用对象

- **内容创作者**：需要将技术文档、博客草稿导出为 PDF 分享
- **文档管理员**：批量整理团队知识库为统一格式的 PDF 归档
- **开发者**：在 CI/CD 流程中将 API 文档、README 自动构建为 PDF 产物

### 1.3 输入输出规格

| 项目 | 规格 |
|------|------|
| 输入来源 | 本地文件路径、标准输入（stdin）、公网 URL |
| 输出格式 | PDF 1.7+（兼容 PDF/A-1b 子集） |
| 输出文件命名 | 默认 `原文件名.pdf`，批量时保留目录结构 |
| 最大输入体积 | 单文件 ≤ 10MB，批处理总数 ≤ 100 个文件 |


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

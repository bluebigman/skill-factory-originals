---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: any2pdf
name: any2pdf
displayName: 文档转PDF 排版输出 格式转换
description: 将Markdown等输入内容转换为排版精良的PDF文档。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/any2pdf
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["any2pdf", "转PDF", "PDF转换", "Markdown转PDF", "文档排版"]

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

# any2pdf — Markdown 到专业排版 PDF 转换技能

## 一、能力边界速查卡

### 1.1 能做什么

| 序号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 格式转换 | 将 Markdown、纯文本、HTML 片段转换为 PDF 文档 |
| 2 | 内容解析 | 识别标题层级、代码块、表格、列表、引用等 Markdown 元素 |
| 3 | 排版优化 | 自动应用页边距、字体层级、代码高亮、表格边框等排版规则 |
| 4 | 批量处理 | 支持一次提交多个文件或 URL，逐个生成 PDF 并汇总报告 |
| 5 | 自定义配置 | 可通过参数调整页面尺寸、字体大小、主题风格（默认/紧凑/宽版） |

### 1.2 不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不处理扫描件 | 不支持 OCR 识别图片中的文字，仅处理文本类输入 |
| 2 | 不执行复杂脚本 | 不运行 Markdown 内嵌的 JavaScript 或外部程序调用 |
| 3 | 不保证像素级还原 | 复杂 CSS 布局或特殊字体可能无法完全还原 |
| 4 | 不处理加密文件 | 受密码保护的 PDF 或加密压缩包不在处理范围内 |
| 5 | 不进行语义改写 | 仅做格式转换，不修改原文内容、措辞或结构 |

### 1.3 适用对象

- 需要将技术文档、会议纪要、学习笔记转为 PDF 的开发者
- 需要批量生成报告附件的办公人员
- 需要统一文档排版风格的内容创作者


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

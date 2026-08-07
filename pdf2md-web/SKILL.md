---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: pdf2md-web
name: pdf2md-web
displayName: PDF转Markdown 网页识别 文本提取
description: 将PDF文件或网页链接转换为结构化Markdown，保留关键信息并标注置信度。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/pdf2md-web
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["PDF转文档", "PDF转Markdown", "PDF识别", "文字提取", "网页转文档", "pdf2md"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# PDF转Markdown 网页识别 文本提取 Skill 文档

## 一、能力边界速查卡

本 Skill 用于将 PDF 文件或网页内容转换为结构化的 Markdown 文档，适用于学习笔记整理、资料归档、信息抽取等场景。

### ✅ 能做（5项核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 数据/文件/URL 输入转换 | 接受用户上传的 PDF 文件或提供的网页 URL，转换为 Markdown 文本 |
| 2 | 关键信息识别与保留 | 自动识别标题、段落、列表、表格、代码块等结构，保留原文层级关系 |
| 3 | 按约定格式输出 | 输出遵循标准 Markdown 语法，包含标题层级、列表、引用、代码块等标记 |
| 4 | 置信度标注 | 对识别不确定的内容（如扫描件模糊文字、复杂表格）标注置信度提示 |
| 5 | 批量处理与自定义格式 | 支持一次处理多个文件，允许用户指定输出格式偏好（如是否保留图片引用） |

### ❌ 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不处理加密或权限受限的 PDF | 需要用户先解除密码保护 |
| 2 | 不识别手写内容 | 仅支持印刷体文字识别 |
| 3 | 不保留原始排版细节 | 如精确字体、字号、颜色、页眉页脚等视觉样式不保留 |
| 4 | 不处理超过 50MB 的超大文件 | 超出后提示用户拆分文件 |
| 5 | 不提供翻译服务 | 仅做格式转换，不改变原文语言 |

### 适用对象

- 需要将 PDF 教材/论文转为可编辑 Markdown 的学生与研究者
- 需要将网页文章保存为本地 Markdown 笔记的知识管理爱好者
- 需要批量整理文档素材的内容运营人员


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

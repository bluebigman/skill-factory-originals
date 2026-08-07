---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: deeppapernote
name: deeppapernote
displayName: 论文精读 Obsidian 笔记生成器
description: 深度阅读单篇论文，自动生成结构化 Obsidian 风格研究笔记。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/deeppapernote
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 知微研读工坊
agent_created: true
trigger_words: ["deeppapernote", "论文精读", "研究笔记", "Obsidian笔记", "文献笔记"]
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

# DeepPaperNote — 论文精读与 Obsidian 研究笔记生成

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| **输入处理** | 接受 PDF 文件路径、URL 链接、纯文本内容、Markdown 草稿 | 无法直接解析扫描版 PDF 中的图片文字（需 OCR 预处理） |
| **信息提取** | 识别标题、作者、机构、摘要、关键词、核心方法、实验数据、结论 | 无法判断论文本身的学术质量或真伪 |
| **笔记生成** | 输出结构化 Markdown，含 YAML frontmatter、章节标题、双向链接建议 | 无法自动创建 Obsidian 库中的实际文件（需用户手动保存） |
| **格式定制** | 支持 3 种预设模板（标准/简洁/详细），可自定义字段 | 无法生成非 Markdown 格式（如 PDF、Word） |
| **批量处理** | 支持一次提交多篇论文（最多 5 篇） | 无法跨论文自动建立关联图谱（需用户在 Obsidian 中手动链接） |

### 1.2 适用对象

- **研究生/科研人员**：需要快速梳理文献核心内容
- **Obsidian 用户**：希望将论文笔记纳入个人知识管理系统
- **学术写作者**：需要为文献综述准备结构化素材

### 1.3 输入输出速览

| 项目 | 说明 |
|------|------|
| **输入来源** | 文件路径（PDF/MD/TXT）、URL、直接粘贴文本 |
| **输出格式** | Markdown 文件，含 YAML frontmatter + 正文结构化笔记 |
| **输出字段** | 元数据、核心问题、方法、结果、局限、个人思考、引用建议 |
| **置信度标注** | 低置信度字段自动标注 `[需核实:字段名]` |


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

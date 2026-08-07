---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: oebfare
name: oebfare
displayName: 博客数据 结构化整理 内容解析
description: 将博客文章、链接或文件解析为结构化数据，便于归档、检索与迁移。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/oebfare
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 技能工坊
agent_created: true
trigger_words: ["oebfare", "博客解析", "内容结构化", "文章归档", "数据整理"]
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

# oebfare — 博客内容结构化解析 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 序号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| 1 | 文章元数据提取 | 从博客 URL 或文本中提取标题、作者、发布日期、标签 | `https://example.com/post/123` |
| 2 | 正文内容清洗 | 去除 HTML 标签、导航噪音，保留正文段落 | 含 `<div>` 的网页源码 |
| 3 | 结构化字段输出 | 按约定 schema 输出 JSON 或 Markdown 表格 | 原始文章文本 |
| 4 | 批量文件处理 | 支持多文件（.md/.html/.txt）批量解析 | 文件夹路径 |
| 5 | 置信度标注 | 对不确定字段标注置信度等级 | 缺失作者信息的文章 |

### 1.2 不能做什么

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不生成新内容 | 不进行摘要、改写、翻译或观点生成 |
| 2 | 不处理图片/音视频 | 仅解析文本内容，不识别媒体文件 |
| 3 | 不访问登录墙 | 需要登录才能访问的页面无法抓取 |
| 4 | 不保证数据完整性 | 源数据缺失时，输出占位符而非猜测值 |
| 5 | 不执行代码 | 不运行页面中的 JavaScript 逻辑 |

### 1.3 适用对象

- 个人博客作者：需要将散落文章整理为结构化档案
- 内容迁移者：从旧平台迁移至新系统前的数据清洗
- 数据分析师：对博客内容进行批量元数据统计


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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: obsidian-skills
name: obsidian-skills
displayName: Obsidian 笔记自动化 数据整理 知识库构建
description: 将任意数据、文件或URL转换为结构化Obsidian笔记，支持CLI操作与开放格式处理。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/obsidian-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["obsidian", "笔记整理", "知识库", "markdown转换", "obsidian skills", "笔记自动化"]

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

# Obsidian Skills — 笔记自动化与知识库构建

## 一、能力边界（一页纸速查卡）

### ✅ 能做（5项核心能力）

| 序号 | 能力 | 说明 | 适用场景示例 |
|------|------|------|--------------|
| 1 | 数据/文件/URL → 结构化笔记 | 将网页、PDF、文本、表格等转换为 Markdown 笔记 | 收藏网页文章、整理会议纪要 |
| 2 | 关键信息识别与保留 | 自动提取标题、作者、日期、标签、核心观点等元数据 | 文献管理、资料归档 |
| 3 | 按约定格式生成输出 | 遵循用户指定的模板或默认 Obsidian 规范（YAML frontmatter + 正文） | 批量导入、模板化笔记 |
| 4 | 置信度标注 | 对不确定的字段标注 `[需核实:字段名]`，不编造内容 | 信息不全时保持诚实 |
| 5 | 批量处理与自定义格式 | 支持多文件/多 URL 同时处理，可自定义输出目录与命名规则 | 整批迁移、定期归档 |

### ❌ 不能做（明确边界）

- 不能访问 Obsidian 官方 API 或云端同步服务（本 Skill 仅操作本地文件与 CLI）
- 不能解析加密文件或需要登录的私有网页内容
- 不能自动执行 Obsidian 插件安装或主题配置
- 不能保证转换后的笔记与 Obsidian 内部链接完全兼容（需人工抽查）
- 不能处理超过 10MB 的单个文件（性能限制）

### 🎯 适用对象

- Obsidian 用户（桌面端/移动端）
- 需要批量整理 Markdown 笔记的内容创作者
- 需要将外部资料系统化导入知识库的研究人员
- 使用 CLI 工具进行自动化工作流的开发者


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

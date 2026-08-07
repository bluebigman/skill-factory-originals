---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: paper-fetch-skill
name: paper-fetch-skill
displayName: 文献获取 批量解析 结构化输出
description: 将文献数据/文件/URL转为结构化结果，支持批量处理与置信度标注。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/paper-fetch-skill
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingDataWorks
agent_created: true
trigger_words: ["paper fetch skill", "文献获取", "论文抓取", "文献解析", "批量文献处理", "文献整理", "论文批量导入"]
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

# 文献获取与结构化处理 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| 输入格式 | 文献 URL、PDF 文件路径、DOI、本地文件目录、纯文本引用信息 | 非文献类网页（新闻、博客等） |
| 处理能力 | 单篇解析、批量解析（≤50 篇/批次）、元数据提取、摘要抽取 | 全文翻译、学术观点评判、引用格式自动生成 |
| 输出形式 | 结构化 JSON、Markdown 表格、CSV 导出 | 直接写入用户本地数据库 |
| 置信度处理 | 对缺失字段标注 `[需核实:字段名]` | 对缺失信息进行猜测补全 |
| 网络请求 | 从公开学术接口获取元数据（如 DOI 解析） | 绕过付费墙获取全文 |

### 1.2 适用对象

- 需要快速整理参考文献列表的研究生、科研人员
- 需要批量导入文献管理工具（如 Zotero、EndNote）的学术工作者
- 需要从零散文献信息中提取结构化数据的图书管理员

### 1.3 边界条件

- 单次批量处理上限：50 条记录
- 单条记录字段上限：12 个核心字段
- 超时阈值：单条 URL 解析 15 秒，超时标记为 `[需核实:网络超时]`


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

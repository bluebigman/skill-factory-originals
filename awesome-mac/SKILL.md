---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: awesome-mac
name: awesome-mac
displayName: macOS 精品软件 分类导航 检索手册
description: 将 macOS 优质软件按场景分类整理，输出结构化检索清单与使用指引。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/awesome-mac
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["awesome mac", "macOS 软件推荐", "Mac 应用清单", "苹果电脑软件导航", "Mac 工具集锦"]

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

# awesome-mac — macOS 软件分类导航 Skill

## 一、能力边界：一页纸速查卡

### 1.1 能做（核心能力）

| 编号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| C1 | 数据/文件/URL 结构化 | 将用户提供的软件列表、网页链接、文本笔记解析为统一格式 | 用户粘贴一段包含 20 个 App 名称的聊天记录 |
| C2 | 关键信息识别与保留 | 自动提取软件名称、类别、付费/免费、适用场景、替代品等字段 | 从 GitHub README 中提取软件仓库信息 |
| C3 | 按约定格式输出 | 生成 Markdown 表格、JSON 数组、CSV 或纯文本清单 | 输出一份按「开发工具 / 日常效率 / 设计创作」分类的清单 |
| C4 | 置信度提示 | 对无法确认的信息标注 `[需核实:字段名]`，不编造数据 | 软件是否收费不确定时，标注 `[需核实:价格]` |
| C5 | 批量处理与自定义格式 | 支持一次处理多条记录，允许用户指定输出字段和排序规则 | 用户要求「只输出免费软件，按名称字母排序」 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不提供下载链接 | 仅输出软件名称和官方来源提示，不生成任何下载地址 |
| L2 | 不评价软件质量 | 不输出「最好用」「强烈推荐」等主观评价，仅做客观分类 |
| L3 | 不保证信息实时性 | 软件价格、是否免费可能随时间变化，输出时标注「信息截至当前时间」 |
| L4 | 不处理非 macOS 软件 | 仅处理 macOS 平台应用，其他平台软件直接忽略并提示 |
| L5 | 不生成安装教程 | 不输出安装步骤、破解方法、激活码等操作指引 |

### 1.3 适用对象

- **目标用户**：需要快速整理 macOS 软件清单的开发者、技术写作者、软件评测人员
- **典型场景**：从收藏夹/笔记/网页中提取软件信息，生成结构化清单；将散乱文本整理为可分享的分类列表
- **不适用场景**：需要实时价格对比、需要软件下载服务、需要安装包分发


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

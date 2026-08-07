---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: anime-dl
name: anime-dl
displayName: 番剧链接处理 资源整理 规范输出
description: 将动漫链接或数据转换为结构化、可复用的规范输出。
version: 1.0.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/anime-dl
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 流云架构师
agent_created: true
trigger_words: ["anime-dl", "动漫下载", "动漫采集", "番剧链接处理", "动漫资源整理", "番剧整理", "动漫链接规范化"]
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

# anime-dl Skill 文档

## 1. 能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入示例 | 输出示例 |
|--------|------|----------|----------|
| 链接解析 | 从用户提供的动漫相关 URL 中提取关键元数据 | `https://example.com/anime/123` | `{ "title": "某番剧", "episode": 12, "source": "example.com" }` |
| 数据规范化 | 将非结构化文本（如聊天消息、笔记）转为统一 JSON 结构 | `"看下 鬼灭之刃 第3集 1080p"` | `{ "title": "鬼灭之刃", "episode": 3, "quality": "1080p" }` |
| 批量处理 | 一次处理多条链接或数据，输出数组结构 | 3 条链接换行输入 | `[ { ... }, { ... }, { ... } ]` |
| 字段补全 | 对缺失字段标注 `[需核实:字段名]` 占位符 | `{ "title": "某番剧" }` | `{ "title": "某番剧", "episode": "[需核实:episode]" }` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不下载文件 | 本 Skill 仅处理元数据，不执行实际下载操作 |
| 不访问外部网站 | 仅基于用户提供的内容进行解析，不主动抓取网页 |
| 不验证链接有效性 | 不检查 URL 是否可访问、资源是否存在 |
| 不处理非动漫内容 | 电影、电视剧、纪录片等非动漫内容不在处理范围内 |
| 不推断缺失信息 | 用户未提供的信息一律用占位符标记，不猜测填充 |

### 1.3 适用对象

- 动漫资源收藏者：需要整理本地或在线番剧链接
- 内容管理助手：需要将散落的动漫信息结构化存储
- 自动化流程开发者：需要标准化的动漫元数据输入


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

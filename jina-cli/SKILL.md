---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: jina-cli
name: jina-cli
displayName: 网页转文本 内容提取 智能解析
description: 将任意URL或文件内容转换为结构化文本，供AI代理直接使用。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/jina-cli
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["jina-cli", "jina cli", "网页转文本", "URL解析", "内容提取", "Reader API", "网页抓取"]
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

# jina-cli — 网页内容转文本工具

## 一、能力边界（一页纸速查卡）

### 能做什么

| 编号 | 能力项 | 说明 | 示例 |
|------|--------|------|------|
| 1 | URL 内容提取 | 将网页链接转换为纯文本或 Markdown | `jina-cli https://example.com/article` |
| 2 | 文件内容解析 | 读取本地文件并转换为结构化文本 | `jina-cli ./notes.txt` |
| 3 | 批量处理 | 一次传入多个 URL 或文件路径 | `jina-cli url1 url2 file1` |
| 4 | 格式自定义 | 通过参数指定输出格式（纯文本/Markdown/JSON） | `jina-cli --format json <url>` |
| 5 | 自检与版本查询 | 验证工具可用性及当前版本 | `jina-cli --selftest` / `--version` |

### 不能做什么

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行 JavaScript 渲染 | 动态页面内容可能无法完整提取 |
| 2 | 不处理登录墙内容 | 需要身份验证的页面无法访问 |
| 3 | 不进行语义理解 | 仅做格式转换，不分析内容含义 |
| 4 | 不保证内容完整性 | 页面结构复杂时可能丢失部分信息 |
| 5 | 不提供翻译服务 | 输出语言与源内容一致 |

### 适用对象

- AI 代理（Agent）需要快速获取网页正文内容时
- 开发者需要将网页转为纯文本进行后续处理时
- 研究人员批量收集网页资料时


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

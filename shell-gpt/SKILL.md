---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: shell-gpt
name: shell-gpt
displayName: 命令行智能助手 任务自动化 数据处理
description: 在终端中调用大模型，将自然语言指令转化为可执行的命令行操作与结构化输出。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/shell-gpt
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 终端工坊
agent_created: true
trigger_words: ["shell-gpt", "命令行助手", "终端智能", "CLI自动化", "shell智能"]

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

# shell-gpt 技能文档

## 1. 能力边界：一页纸速查卡

### 1.1 能做（核心能力清单）

| 序号 | 能力项 | 说明 | 典型场景 |
|------|--------|------|----------|
| 1 | 自然语言转命令 | 将中文/英文描述转换为可执行的 shell 命令 | "找出当前目录下最大的5个文件" |
| 2 | 数据文件结构化 | 从 CSV、JSON、日志等文件中提取关键字段并重组 | 从 access.log 提取 IP 与状态码 |
| 3 | URL 内容摘要 | 抓取网页正文并提炼要点 | 总结一篇技术博客的核心观点 |
| 4 | 批量任务编排 | 对多文件/多输入执行同一套处理逻辑 | 批量重命名、批量格式转换 |
| 5 | 输出格式定制 | 按指定格式（表格、JSON、Markdown）输出结果 | 将命令结果转为 JSON 供下游消费 |

### 1.2 不能做（明确边界）

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行交互式命令 | 不处理需要 TTY 持续交互的程序（如 vim、top） |
| 2 | 不访问受保护系统 | 不绕过权限验证、不读取 `/etc/shadow` 等敏感文件 |
| 3 | 不保证命令绝对正确 | 生成的命令需人工复核后再执行，尤其是 `rm`、`dd` 等危险操作 |
| 4 | 不处理二进制大文件 | 超过 10MB 的二进制文件不做内容解析 |
| 5 | 不联网获取实时数据 | 仅处理用户提供的 URL 或本地文件，不主动爬取外部资源 |

### 1.3 适用对象

- **终端重度用户**：日常需要处理文件、日志、批量操作
- **运维/开发人员**：需要快速生成脚本或解析日志
- **数据分析初学者**：不熟悉命令行但需要处理数据文件


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

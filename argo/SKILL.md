---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: argo
name: argo
displayName: 代码审计 漏洞扫描 静态分析
description: 让AI像资深审计员一样阅读源码，定位潜在安全弱点。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/argo
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: CodeSentinel
agent_created: true
trigger_words: ["argo", "漏洞扫描", "代码审计", "安全检测", "静态分析", "vulnerability scan", "code audit"]
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

# Argo Skill 文档

## 一、能力边界速查卡

本 Skill 将 AI 模型转化为一个本地代码审计助手。它不依赖外部数据库，而是通过模型自身的语义理解能力，对指定目录下的源代码进行逐行审查，寻找可能被利用的安全弱点。

### 1.1 核心能力清单

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 本地目录扫描 | 递归读取指定文件夹内的所有文本类源码文件 | `扫描 ./src` |
| 多语言识别 | 自动识别文件类型（Python/JS/Java/Go/C++等） | `.py`, `.js`, `.java` |
| 漏洞模式匹配 | 基于模型知识库识别已知危险函数调用与不安全写法 | `eval()`, `exec()`, `innerHTML` |
| 上下文关联分析 | 结合变量赋值、数据流走向判断漏洞是否真实可利用 | 输入是否来自用户且未过滤 |
| 严重等级评估 | 对发现的每个问题给出 高/中/低 三档评级 | 远程代码执行 → 高危 |
| 修复建议生成 | 针对每个漏洞提供具体的代码修改方向 | 使用参数化查询替代字符串拼接 |
| 结果结构化输出 | 以 Markdown 表格或 JSON 格式输出审计报告 | 见下文输出规范 |

### 1.2 能力边界（不能做什么）

| 限制项 | 说明 |
|--------|------|
| 不执行动态分析 | 不会运行代码，无法检测运行时才暴露的问题（如内存泄漏） |
| 不保证穷尽所有漏洞 | 依赖模型训练知识，0-day 或高度混淆的代码可能漏报 |
| 不处理二进制文件 | 仅解析文本类源码，`.exe`, `.so`, `.class` 等文件会跳过 |
| 不自动修复代码 | 仅提供建议，修改动作由用户自行完成 |
| 不连接外部 CVE 数据库 | 漏洞情报基于模型内置知识，非实时更新 |

### 1.3 适用对象

- **个人开发者**：提交代码前快速自查
- **安全工程师**：作为人工审计的辅助预筛工具
- **技术管理者**：了解项目整体的安全健康度


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

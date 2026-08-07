---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: deepsec
name: deepsec
displayName: 安全审计 代码风险 依赖检测
description: 深度安全审计工具，检测AI生成代码中的恶意依赖与配置缺陷。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/deepsec
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["deepsec", "安全审计", "代码风险检测", "依赖安全", "AI代码审查"]
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

# DeepSec — AI 安全攻防平台 Skill 使用指南

## 一、能力边界：一页纸速查卡

### 1.1 核心能力清单

| 序号 | 能力项 | 说明 | 输入类型 | 输出类型 |
|------|--------|------|----------|----------|
| 1 | 数据/文件/URL 结构化转换 | 将原始输入解析为统一结构 | 文本、文件路径、URL | JSON 结构化数据 |
| 2 | 关键信息识别与保留 | 提取输入中的核心字段，保留上下文 | 任意格式 | 字段映射表 |
| 3 | 约定格式输出 | 按预定义 schema 生成结果 | 结构化数据 | JSON/YAML/CSV |
| 4 | 置信度标注 | 对每个输出字段标注可信程度 | 分析结果 | 0.0~1.0 浮点数 |
| 5 | 批量处理与自定义格式 | 支持多文件/多 URL 并行处理 | 数组/列表 | 批量结果集 |

### 1.2 能力边界声明

**能做：**
- 解析用户提供的代码文件、依赖清单、配置文件
- 识别已知的恶意包名、可疑依赖关系
- 检测缺失的安全配置项（如认证、加密、权限控制）
- 对分析结果给出置信度评分
- 支持批量扫描和自定义输出模板

**不能做：**
- 无法执行代码，不进行运行时动态分析
- 不保证发现所有安全漏洞（静态分析固有局限）
- 不替代人工安全审计决策
- 不提供漏洞利用或攻击代码
- 不连接外部漏洞数据库（离线模式）

**适用对象：**
- AI 辅助开发场景下的代码审查
- CI/CD 流水线中的预检环节
- 安全团队的前置筛选工具
- 开发者自检 AI 生成代码的安全性


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

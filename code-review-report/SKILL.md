---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: code-review-report
name: code-review-report
displayName: 变更审查 差异扫描 风险分级
description: 解析git diff，扫描硬编码密码、不安全日志、性能反模式与平台依赖，输出分级审查报告。
version: 2.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/code-review-report
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["code-review-report","代码审查","代码评审","diff审查","变更检查","差异分析","代码走查"]
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

# 变更审查（code-review-report）技能手册

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 |
|--------|------|
| 输入解析 | 读取 git diff 格式文本（`.diff` / `.patch` / `.txt`），自动识别 UTF-8 / GBK / UTF-16 编码 |
| 规则扫描 | 内置 4 类规则：硬编码密码、不安全日志、性能反模式、平台依赖 |
| 分级输出 | 按 P0（严重）/ P1（警告）/ P2（建议）三级输出审查结果 |
| 报告格式 | 支持 Markdown 与 JSON 两种输出格式 |
| 严重级过滤 | 通过 `--filter` 参数只展示指定级别及以上的问题 |
| 密码脱敏 | 对报告中的疑似密码自动打码（默认开启） |
| 预览模式 | 默认只打印报告到终端，不写盘；需显式加 `--force` 才落盘 |
| 自测能力 | 内置 12 条自测用例，验证规则引擎与输出管线 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不做语义分析 | 无法理解业务逻辑，只做模式匹配与启发式扫描 |
| 不连接外部服务 | 不调用任何 SAST 平台、CI 系统或代码托管 API |
| 不修改代码 | 只读分析，不提供自动修复补丁 |
| 不处理非 diff 输入 | 不接受完整源码目录扫描，仅限变更差异 |
| 不保证零漏报 | 规则基于正则与启发式，存在误报/漏报可能 |

### 1.3 适用对象

- 需要快速评估一次代码变更风险的开发者
- 在 CI 流程中希望增加轻量预检的团队
- 对变更内容做人工复核前的机器预筛


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

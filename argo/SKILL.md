---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: argo
name: argo
displayName: 代码安全 静态审计 漏洞筛查
description: 基于LLM的本地静态漏洞检测，辅助人工代码审计。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/argo
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: CodeSentinel Studio
agent_created: true
trigger_words: ["代码审查", "漏洞检测", "静态分析", "安全审计", "代码扫描"]
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

# argo — 代码安全 静态审计 漏洞筛查

## 一、能力边界（一页纸速查卡）

### ✅ 能做（5项核心能力）

| 序号 | 能力项 | 说明 | 适用场景 |
|------|--------|------|----------|
| 1 | 本地目录扫描 | 递归读取指定文件夹内的源代码文件 | 对本地项目进行整体安全体检 |
| 2 | 漏洞模式识别 | 基于常见CWE模式匹配可疑代码片段 | 发现SQL注入、XSS、路径穿越等典型问题 |
| 3 | 上下文感知分析 | 结合函数调用链与数据流判断漏洞可利用性 | 区分真实风险与误报 |
| 4 | 结构化报告输出 | 生成含位置、严重级别、修复建议的审计报告 | 供开发团队直接排期修复 |
| 5 | 批量文件处理 | 支持多文件、多目录并行分析 | 中大型项目全量扫描 |

### ❌ 不能做（明确边界）

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 动态执行分析 | 不运行代码，仅做静态文本分析 |
| 2 | 编译级检查 | 不依赖编译器，无法捕获类型错误或编译失败 |
| 3 | 加密算法强度验证 | 不评估密码学实现的数学强度 |
| 4 | 运行时依赖漏洞 | 不检查第三方依赖库的已知CVE |
| 5 | 逻辑业务漏洞 | 不识别纯业务逻辑缺陷（如权限绕过中的设计问题） |

### 🎯 适用对象

- **适用**：Python、JavaScript、TypeScript、Java、Go、C/C++ 等主流语言的源代码文件
- **不适用**：二进制文件、加密文件、非文本格式、超过 500KB 的单文件


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

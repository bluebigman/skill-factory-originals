---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: tach
name: tach
displayName: 依赖可视化 架构守护 边界检查
description: 解析项目依赖关系，可视化架构边界并执行一致性校验。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/tach
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Ling
agent_created: true
trigger_words: ["tach", "依赖可视化", "架构边界", "依赖检查", "模块约束", "依赖分析"]
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

# tach — 依赖可视化与架构边界守护

## 一、能力边界（一页纸速查卡）

### ✅ 能做（核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 依赖关系解析 | 解析 Python 项目中的模块导入关系，生成结构化依赖图 |
| 2 | 架构边界校验 | 依据用户定义的模块边界规则，检查是否存在越界依赖 |
| 3 | 可视化输出 | 将依赖关系渲染为文本树、表格或 DOT 格式图形描述 |
| 4 | 增量检查 | 支持对指定文件/目录的定向检查，快速定位违规点 |
| 5 | 规则自定义 | 允许用户通过配置文件声明模块归属与允许的依赖方向 |

### ❌ 不能做（明确限制）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行代码 | 仅做静态分析，不运行被测项目代码 |
| 2 | 不自动修复 | 发现违规后仅报告位置与原因，不修改源码 |
| 3 | 不支持动态导入分析 | 对 `__import__`、`importlib.import_module` 等运行时导入不做深度追踪 |
| 4 | 不处理跨语言依赖 | 仅关注 Python 模块间的导入关系 |
| 5 | 不保证覆盖所有边界场景 | 对条件导入、循环导入等复杂场景可能产生误报或漏报 |

### 🎯 适用对象

- 维护中型以上 Python 项目的开发团队
- 需要强制模块分层（如 MVC、六边形架构）的代码库
- 在 CI 流程中增加架构守护环节的工程团队


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

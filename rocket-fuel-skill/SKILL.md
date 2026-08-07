---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: rocket-fuel-skill
name: rocket-fuel-skill
displayName: 双引擎协作 代码审查 质量门禁
description: 双AI协作代码审查与质量门禁，自动生成结构化审查报告。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/rocket-fuel-skill
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["代码审查", "code review", "双AI协作", "质量门禁", "审查报告"]
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

# rocket-fuel-skill 技能文档

## 一、能力边界速查卡

### 1.1 核心能力清单

| 序号 | 能力项 | 说明 | 适用场景 |
|------|--------|------|----------|
| 1 | 双引擎审查 | 调用 Fable 5 与 Codex 双模型并行审查，输出综合结论 | 代码合并前质量把关 |
| 2 | 结构化报告 | 将审查结果整理为固定字段的 Markdown 报告 | 团队评审、归档记录 |
| 3 | 关键信息提取 | 自动识别代码中的函数、类、依赖、潜在缺陷 | 代码走查、技术债盘点 |
| 4 | 置信度标注 | 对每条审查结论标注可信程度（高/中/低） | 辅助决策、风险分级 |
| 5 | 批量处理 | 支持多文件、多目录、URL 仓库的批量审查 | 版本发布前全量检查 |

### 1.2 能力边界声明

**能做：**
- 解析本地代码文件、Git 仓库目录、公开代码 URL
- 识别语法错误、逻辑漏洞、安全风险、性能瓶颈
- 输出统一格式的审查报告（含字段：文件路径、行号、问题类型、严重级别、置信度、修复建议）
- 支持自定义审查规则（通过配置文件传入）

**不能做：**
- 不能直接修改代码文件（仅输出建议）
- 不能执行代码或运行测试用例
- 不能访问私有仓库或需要认证的远程资源
- 不能替代人工评审的最终决策

### 1.3 适用对象

- 开发团队：合并请求（MR/PR）前的自动化预审
- 技术管理者：获取代码质量趋势报告
- 独立开发者：提交前自检


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

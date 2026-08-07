---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: skill-based-architecture
name: skill-based-architecture
displayName: 技能工厂 代码库萃取 规则蒸馏
description: 将任意代码库转化为可复用技能包，提炼规则、流程与经验。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/skill-based-architecture
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Ling
agent_created: true
trigger_words: ["skill-based-architecture", "技能萃取", "代码库分析", "规则蒸馏", "工作流提炼", "项目经验沉淀"]
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

# 技能工厂：代码库萃取与规则蒸馏

## 一、能力边界（一页纸速查卡）

### 能做（核心能力清单）

| 序号 | 能力项 | 说明 | 输入示例 | 输出示例 |
|------|--------|------|----------|----------|
| 1 | 代码库结构解析 | 扫描目录树、识别模块边界、定位关键配置文件 | `/src`、`/lib`、`/config` | 模块依赖图、目录说明文档 |
| 2 | 规则与约定提取 | 从代码注释、命名规范、CI 脚本中提炼隐性规则 | `.eslintrc`、`Makefile`、`README` 中的约定 | 规则清单（含优先级与适用范围） |
| 3 | 工作流还原 | 梳理构建、测试、发布等流程的步骤与顺序 | `package.json` scripts、`.github/workflows` | 流程时序图、步骤说明表 |
| 4 | 经验教训沉淀 | 识别代码中的 workaround、TODO、FIXME 及注释中的决策记录 | `// HACK:`、`// NOTE:`、`// XXX:` | 经验卡片（背景、决策、后果） |
| 5 | 技能包生成 | 将上述产物整合为符合 Skill 规范的文档包 | 上述所有输出 | `SKILL.md` + 辅助资源文件 |

### 不能做（明确边界）

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行代码 | 仅做静态分析与文本解析，不运行、不编译、不调试目标代码库 |
| 2 | 不保证完整性 | 无法覆盖未写入代码或文档的隐性知识（如口头约定、离线决策） |
| 3 | 不替代人工判断 | 提取出的规则需由领域专家复核后方可视为有效 |
| 4 | 不处理二进制依赖 | 仅分析文本类文件（源码、配置、文档），不解析 `.so`、`.dll`、`.jar` 等二进制 |
| 5 | 不跨库合并 | 一次仅处理单一代码库，不自动合并多个项目的规则 |

### 适用对象

- **目标代码库**：Git 管理的源码项目，包含至少一个配置文件（如 `package.json`、`pom.xml`、`Cargo.toml`、`go.mod`、`requirements.txt` 等）
- **使用者**：需要快速上手陌生项目的开发者、需要将项目经验文档化的技术负责人、需要建立团队规范的工具链维护者
- **不适用**：纯二进制分发项目、无任何文本说明的遗留系统、包含敏感信息且未脱敏的私有仓库


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

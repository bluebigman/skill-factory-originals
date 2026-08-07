---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: github-datasource
name: github-datasource
displayName: 代码仓数据接入 解析转换 结构化输出
description: 将Git代码仓数据/文件/URL转换为结构化结果，支持批量处理与置信度标注。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/github-datasource
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataFlow Studio
agent_created: true
trigger_words: ["github datasource", "Git代码管理", "数据可视化", "仓库数据接入", "代码仓解析"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# GitHub 数据源接入与结构化处理 Skill

## 一、能力边界速查卡（一页纸）

### 1.1 能做（核心能力）

| 编号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| C1 | 数据/文件/URL 结构化 | 将用户提供的原始数据、文件内容或远程 URL 解析为统一结构 | `https://github.com/.../data.csv`、本地 `repo_list.txt` |
| C2 | 关键信息识别与保留 | 自动提取仓库名、分支、提交哈希、文件路径、语言类型等关键字段 | 一段含仓库地址的文本 |
| C3 | 约定格式输出 | 按用户指定或默认的 JSON/CSV/Markdown 表格格式输出结果 | `--format json` |
| C4 | 置信度标注 | 对每条输出记录标注置信度等级（高/中/低）及不确定字段 | `confidence: 0.92` |
| C5 | 批量处理与自定义格式 | 支持多文件/多 URL 批量输入，允许用户自定义输出字段子集 | 传入 10 个 URL，只输出 `repo_name` 和 `stars` |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行代码 | 本技能只做数据解析与转换，不运行、编译或测试仓库中的代码 |
| L2 | 不访问私有仓库 | 无凭据时无法获取私有仓库内容，仅处理公开数据或用户直接提供的内容 |
| L3 | 不推断缺失值 | 原始数据中不存在的字段，输出 `[需核实:字段名]` 占位，不猜测填充 |
| L4 | 不保证数据时效性 | 远程 URL 抓取结果反映抓取时刻状态，不承诺实时同步 |

### 1.3 适用对象

- 需要将 GitHub 仓库元数据、文件列表、提交记录等整理为表格/JSON 的开发者
- 需要批量对比多个仓库信息的调研人员
- 需要将仓库数据导入其他工具（如 BI 平台、文档系统）的自动化流程设计者


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

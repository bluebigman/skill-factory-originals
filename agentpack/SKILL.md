---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agentpack
name: agentpack
displayName: 本地上下文引擎 任务路由 文件定位
description: 为AI编码代理提供本地上下文路由，精准定位文件、测试、规则与技能。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agentpack
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨
agent_created: true
trigger_words: ["agentpack", "本地上下文", "任务路由", "文件定位", "上下文引擎", "代码代理导航"]

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

# agentpack — 本地上下文引擎 Skill 文档

## 一、能力边界：一页纸速查卡

### 1.1 能做什么（核心能力清单）

| 序号 | 能力项 | 具体说明 | 典型应用场景 |
|------|--------|----------|--------------|
| 1 | 数据/文件/URL 结构化转换 | 将用户提供的原始输入（文本、代码文件、网页链接）解析为结构化结果 | 把一段报错日志转为 JSON 格式的故障摘要 |
| 2 | 关键信息识别与保留 | 从输入中提取任务相关的核心要素（路径、函数名、测试用例、规则条目） | 从需求描述中抓取涉及的文件路径与修改点 |
| 3 | 约定格式输出 | 按照预定义的字段结构生成结果，保证下游工具可直接消费 | 输出 `{task, files[], tests[], rules[], skills[]}` 结构 |
| 4 | 置信度标注 | 对每个输出字段标注可信程度，区分确定信息与推测信息 | 对推断出的文件路径标注 `confidence: 0.6` |
| 5 | 批量处理与自定义格式 | 支持一次处理多个输入项，并允许用户指定输出模板 | 一次分析 10 个相关 issue 并汇总为表格 |

### 1.2 不能做什么（明确边界）

| 序号 | 禁止事项 | 原因说明 |
|------|----------|----------|
| 1 | 不执行代码修改 | 本引擎只做上下文路由与信息整理，不直接改动任何源文件 |
| 2 | 不保证路径绝对正确 | 文件路径推断基于规则与启发式，存在误差可能 |
| 3 | 不处理无输入的情况 | 必须至少提供一个数据源（文本/文件/URL）才能启动 |
| 4 | 不跨项目记忆 | 每次运行独立，不保留历史会话状态 |
| 5 | 不替代人工判断 | 最终的任务决策权在用户手中，引擎只提供建议 |

### 1.3 适用对象

- **AI 编码代理**：作为工具链中的上下文路由层，帮助代理快速定位相关文件与规则。
- **开发者**：在 IDE 或命令行中手动调用，快速梳理项目结构。
- **技术文档撰写者**：需要从代码库中提取结构化信息用于文档生成。


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

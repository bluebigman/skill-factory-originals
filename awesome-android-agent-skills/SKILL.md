---
> 本内容由 AI 生成，仅供学习参考（《人工智能生成合成内容标识办法》显式标识）。
<!-- ai-generated-notice -->
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: awesome-android-agent-skills
name: awesome-android-agent-skills
displayName: Android技能导航 任务编排与执行
description: 面向Android智能体的技能检索、编排与执行辅助工具。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/awesome-android-agent-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["awesome android agent skills", "android技能", "技能编排", "android agent", "技能导航"]
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

# awesome-android-agent-skills 技能文档

## 一、能力边界：一页纸速查卡

本技能面向 **Android 智能体（Agent）开发者与使用者**，用于在 `awesome-android-agent-skills` 生态中快速定位、筛选、组合可复用的技能模块，并输出结构化的技能调用方案。

| 维度 | 说明 |
|------|------|
| **核心用途** | 将用户输入的技能需求（自然语言描述 / 技能名称 / 场景关键词）解析为结构化的技能匹配结果与执行建议 |
| **输入类型** | ① 自然语言需求描述 ② 技能名称或关键词列表 ③ 包含技能清单的 URL 或文件路径 |
| **输出类型** | Markdown 格式的技能匹配报告，包含：匹配技能列表、置信度评分、组合建议、前置依赖说明 |
| **处理上限** | 单次最多解析 20 个技能条目；超出部分截断并提示用户分批提交 |
| **批量模式** | 支持通过 `--batch` 参数传入 JSON 文件（格式见下文），一次处理多组需求 |

### 能做（5 项核心能力）

1. **需求解析**：从用户输入中提取技能相关的关键实体（技能名、版本号、平台要求、功能关键词）。
2. **技能匹配**：基于内置的 `awesome-android-agent-skills` 索引库，返回匹配度 Top 5 的技能条目。
3. **组合建议**：当单个技能无法覆盖需求时，推荐 2-3 个技能的串联组合方案。
4. **置信度标注**：每条匹配结果附带 0-1 的置信度分数，低于 0.6 时明确标注 `[需核实]`。
5. **格式转换**：支持将匹配结果导出为 JSON / Markdown / CSV 三种格式。

### 不能做（明确边界）

- ❌ 不执行任何 Android 代码或调用真实 API——本技能仅做信息检索与编排建议。
- ❌ 不保证匹配结果的绝对正确性——技能库持续更新，结果仅供参考。
- ❌ 不处理与 Android 技能无关的通用问题（如财务、医疗建议）。
- ❌ 不存储用户输入数据——所有处理均在会话内完成，不写入持久化存储。

### 适用对象

- **初级用户**：不知道有哪些技能可用，需要导航与推荐。
- **进阶用户**：有明确技能需求，需要快速比对多个候选技能。
- **开发者**：需要将技能组合嵌入自己的 Agent 工作流。


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

## 前置条件

- Python 3.9+（脚本依赖标准库，无需联网即可运行自检）
- 已获取待处理的输入文件，并对其拥有合法使用权
- 建议先在样本数据上试运行，确认输出符合预期后再批量处理

## 执行步骤

1. **准备输入**：将待处理文件放入同一目录，确认命名规范一致。
2. **试运行**：先用单个样本执行，核对输出字段与格式。
3. **批量执行**：确认无误后对全量数据执行，并保留原始文件备份。
4. **校验结果**：抽查输出条目，核对关键字段与源数据一致。

## 输出

- 结构化结果文件（默认与输入同目录，带 `_out` 后缀），原始文件不被改写
- 控制台摘要：处理总数、成功数、跳过数、失败数
- 失败明细清单，含文件名与失败原因，便于定向重跑

## 异常处理

| 异常情况 | 表现 | 处理方式 |
|---|---|---|
| 输入文件不存在 | 提示路径错误并退出 | 核对路径，使用绝对路径重试 |
| 文件格式不符 | 该条跳过并计入失败明细 | 转换为受支持格式后重跑该条 |
| 权限不足 | 写入失败 | 更换输出目录或提升目录写权限 |
| 单条数据异常 | 跳过该条，继续处理其余 | 处理结束后查看失败明细定向重跑 |

失败处理原则：**单条失败不中断整批**，全部异常汇总到失败明细，支持只重跑失败项。

## 稳定性保障

- **超时控制**：单条处理设置上限，超时自动跳过并记入失败明细，避免整批卡死。
- **重试策略**：可恢复类错误（临时占用、瞬时 IO 失败）自动重试 3 次，间隔递增。
- **降级方案**：高级解析失败时自动回退到基础解析模式，保证有可用输出而非直接报错。
- **幂等性**：重复执行同一批输入结果一致，不会产生重复追加。

## FAQ 与反模式

**Q：可以直接对原始文件覆盖写入吗？**
A：不建议。默认输出到独立文件，保留原始数据是可回溯的前提。

**Q：处理到一半失败了怎么办？**
A：已完成部分的输出有效，查看失败明细后只重跑失败项即可，无需整批重来。

**反模式 ①**：不做试运行直接批量处理全量数据 —— 参数配错会一次性污染全部输出。

**反模式 ②**：忽略失败明细只看成功数 —— 静默跳过的条目会造成数据缺口。

**反模式 ③**：把工具输出直接作为最终结论 —— 关键字段务必人工抽检。

## 安全声明

- 全流程本地执行，不上传任何用户数据到第三方服务。
- 不读取与任务无关的目录，不写入系统目录。
- 处理含个人信息的数据时，请自行遵守《个人信息保护法》等相关法规。
- 本 Skill 代码由 AI 辅助生成并经自检验证，以 MIT 协议开源，使用者自负使用后果。

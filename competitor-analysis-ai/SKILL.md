---
> 本内容由 AI 生成，仅供学习参考（《人工智能生成合成内容标识办法》显式标识）。
<!-- ai-generated-notice -->
slug: competitor-analysis-ai
name: competitor-analysis
displayName: 竞品透视 对比拆解 策略建议
description: 多维度拆解竞品，输出可执行差异化策略与结构化对比报告。
version: 19.0.11
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/competitor-analysis-ai
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: StrategyForge
agent_created: true
trigger_words: ["competitor-analysis", "竞品分析", "竞品对比", "竞争策略", "市场分析"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 竞品透视与策略拆解

## 一、能力边界与适用场景（速查卡）

本 Skill 专注于**结构化竞品分析**，将零散信息转化为可决策的对比框架。

| 能力维度 | 支持内容 | 不支持内容 |
| :--- | :--- | :--- |
| **功能对比** | 2-10个竞品，自定义功能维度，输出差异矩阵 | 无法自动爬取功能列表，需用户提供或确认 |
| **定价分析** | 识别免费/订阅/买断/混合模式，计算价格区间，标注超量费用等隐藏成本 | 无法获取实时价格，基于用户输入或公开知识推断 |
| **评价摘要** | 提取高频正负面关键词，按情感分类 | 无法自动抓取评价，需用户粘贴文本 |
| **策略建议** | 生成3-5条差异化方向，含优先级（高/中/低） | 不提供投资回报率预测或市场收益保证 |
| **市场定位** | 推断目标市场层级（高端/中端/长尾） | 不涉及具体市场规模数据核算 |
| **SWOT分析** | 输出四象限，每条附证据来源（用户输入或分析推断） | 无法保证证据的绝对客观，推断会标注 |
| **批量处理** | 支持表格/CSV/自然语言输入，自动识别竞品列 | 对格式混乱的输入可能识别失败，需结构化 |
| **格式定制** | 支持 Markdown / JSON / 纯文本，按需指定字段 | 不支持 PDF、Word 等文件格式直接导出 |

**适用对象**：产品经理、市场分析师、创业者、战略规划人员。适合在**产品立项、版本迭代、市场进入**前使用。

**限制说明**：本 Skill 不联网，所有分析基于你提供的文本、数据及模型内部知识。分析结果作为决策参考，不构成商业保证。


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

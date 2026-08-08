---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: jf-writing-skill
name: jf-writing-skill
displayName: 金融论文 学术写作 风格校准
description: 基于金融经济学期刊风格库，辅助学术写作的格式校准与表达优化。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/jf-writing-skill
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["翻译润色", "学术润色", "金融写作", "论文风格", "JF风格", "经济学期刊", "学术表达优化"]

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

# 金融论文 学术写作 风格校准（jf-writing-skill）

## 一、能力边界：一页纸速查卡

### 1.1 能做（核心能力清单）

| 编号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| C1 | 文本风格转换 | 将口语化/非正式表达转换为金融学期刊惯用的正式学术语体 | "股票涨了不少" → "股票价格呈现显著上行趋势" |
| C2 | 结构合规检查 | 核对摘要、引言、文献综述、假设提出、数据描述、实证结果、结论的章节完整性 | 提供论文段落，检查是否缺少假设编号或数据来源说明 |
| C3 | 术语一致性校准 | 同一概念在全文使用统一译名或英文术语，避免混用 | "公司治理"与"corporate governance"混用时的统一建议 |
| C4 | 句式精炼建议 | 对冗长句、被动滥用、模糊指代给出改写方案 | "It is important to note that..." 类冗余引导句的删改 |
| C5 | 引用格式核对 | 检查作者-年份引用与参考文献列表的对应关系 | 文中引用 (Smith, 2020) 但文末列表缺失时的标记 |

### 1.2 不能做（明确拒绝项）

| 编号 | 拒绝项 | 原因 |
|------|--------|------|
| R1 | 代写整篇论文 | 本 Skill 仅提供修改建议与风格校准，不替代原创写作 |
| R2 | 数据造假或结果篡改 | 不提供任何伪造实证结果的建议 |
| R3 | 期刊投稿保证 | 不承诺任何期刊录用结果 |
| R4 | 超越金融学领域的润色 | 医学、工程等其他学科的表达习惯不在本 Skill 知识库内 |
| R5 | 法律或合规意见 | 涉及学术伦理争议时仅提示风险，不给出裁决 |

### 1.3 适用对象

- 金融学、经济学硕博研究生
- 金融领域青年学者
- 金融专业本科毕业论文写作者
- 需要向金融学期刊投稿的研究人员


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

---
> 本内容由 AI 生成，仅供学习参考（《人工智能生成合成内容标识办法》显式标识）。
<!-- ai-generated-notice -->
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: awesome-journal-skills
name: awesome-journal-skills
displayName: 期刊投稿 格式匹配 学术导航
description: 面向主流学术期刊的投稿格式与要求速查工具包，覆盖经管、综合及中文核心期刊。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/awesome-journal-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Lab
agent_created: true
trigger_words: ["awesome journal skills", "期刊技能", "投稿格式", "journal skills", "期刊要求查询", "投稿指南"]
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

# awesome-journal-skills 技能文档

## 一、能力边界：一页纸速查卡

本技能面向需要向主流学术期刊投稿的研究人员、学生及科研助理，提供期刊信息查询、格式匹配与投稿前检查的辅助能力。

### 1.1 能做清单

| 序号 | 能力项 | 说明 | 示例 |
|------|--------|------|------|
| 1 | 期刊信息解析 | 从用户提供的期刊名称、ISSN、官网 URL 中提取结构化信息 | 输入 "AER"，输出 American Economic Review 的基本档案 |
| 2 | 格式要求匹配 | 根据目标期刊返回投稿格式要点（摘要、参考文献、图表规范） | 输入 "Nature 格式"，返回摘要字数限制、文献引用风格 |
| 3 | 批量处理 | 支持一次提交多个期刊名称或文件，返回对照表 | 输入 "AER, QJE, 经济研究"，输出三列对比清单 |
| 4 | 置信度标注 | 对不确定的信息输出 `[需核实:字段]` 占位，不编造 | 期刊最新影响因子未知时标注 `[需核实:影响因子]` |
| 5 | 自定义输出 | 用户可指定输出格式（表格 / 清单 / 对比视图） | 输入 "用表格输出"，返回 Markdown 表格 |

### 1.2 不能做清单

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不保证信息实时性 | 期刊要求可能更新，本技能不承诺数据为最新版本 |
| 2 | 不替代官方指南 | 最终投稿请以期刊官网的 author guidelines 为准 |
| 3 | 不提供投稿建议 | 不判断稿件是否适合某期刊，不预测录用概率 |
| 4 | 不处理付费内容 | 不解析需要订阅或购买的期刊内部资料 |

### 1.3 适用对象

- 初次投稿、不熟悉目标期刊格式要求的研究人员
- 需要同时比对多个期刊格式要求的课题组
- 学术写作课程中需要了解期刊规范的师生


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

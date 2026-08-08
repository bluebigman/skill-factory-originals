---
> 本内容由 AI 生成，仅供学习参考（《人工智能生成合成内容标识办法》显式标识）。
<!-- ai-generated-notice -->
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: marketing-platform
name: marketing-platform
displayName: 营销数据解析与合规审查
description: 将营销平台数据文件转为结构化结果，辅助条款合规审查。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/marketing-platform
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Studio
agent_created: true
trigger_words: ["合同审查", "营销平台", "条款解析", "数据转结构化", "合规审查", "协议分析"]
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

# 营销数据解析与合规审查 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 编号 | 能力项 | 说明 | 输入示例 | 输出示例 |
|------|--------|------|----------|----------|
| C1 | 数据/文件/URL 结构化 | 将用户提供的文本、文件路径或网页链接内容，解析为字段化数据 | 一份营销平台服务条款的 PDF 文本 | `{"条款名称":"...","生效日期":"...","关键义务":[...]}` |
| C2 | 关键信息识别与保留 | 自动提取输入中的实体、日期、金额、义务条款等核心要素 | 合同中包含"违约金 5 万元" | 输出中保留 `违约金:50000` 字段 |
| C3 | 约定格式输出 | 按用户指定的字段结构或默认模板生成结果 | 用户要求"输出 JSON，含 summary 字段" | 按 JSON 结构返回 |
| C4 | 置信度标注 | 对每项输出字段标注可信程度（高/中/低），不确定时明确提示 | 条款存在歧义 | `{"置信度":"中","说明":"条款表述模糊"}` |
| C5 | 批量处理与自定义格式 | 支持多文件/多 URL 同时处理，支持用户自定义输出模板 | 一次传入 3 个 URL | 返回 3 组结构化结果 |

### 1.2 不能做什么

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不提供法律意见 | 本 Skill 仅做文本解析与结构整理，不构成法律建议或合同效力判断 |
| L2 | 不执行自动化操作 | 不代为提交表单、不调用外部 API 进行数据写入 |
| L3 | 不处理非文本内容 | 图片中的文字需先经 OCR 转为文本后方可处理 |
| L4 | 不保证数据完整性 | 若输入内容缺失或截断，输出中会标注 `[需核实:字段名]`，不做臆测补全 |
| L5 | 不替代人工审核 | 结构化结果需由使用者自行复核，特别是涉及权利义务的条款 |

### 1.3 适用对象

- **目标用户**：市场营销人员、运营专员、法务助理、数据分析师
- **典型场景**：营销平台（如广告投放、数据分析工具）服务条款的快速梳理、数据导出文件的字段整理、多份协议的结构化对比
- **不适用场景**：需要深度法律推理的合同纠纷分析、需要实时数据抓取的动态网页处理


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

---
> 本内容由 AI 生成，仅供学习参考（《人工智能生成合成内容标识办法》显式标识）。
<!-- ai-generated-notice -->
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ailaw1
name: ailaw1
displayName: 合同智审 法律风险 条款比对
description: 多维度智能合同审查工具，辅助识别法律风险与条款缺失。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ailaw1
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LegalForge Studio
agent_created: true
trigger_words: ["合同审查", "合同分析", "法律风险", "条款比对", "合同体检", "审合同"]
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

# 合同智审 · 多维度法律风险分析 Skill 文档

## 一、能力边界速查卡（一页纸）

### 1.1 能做（核心能力清单）

| 序号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| C1 | 多源数据接入 | 支持用户直接粘贴文本、上传文件（.txt/.docx/.pdf）、提供 URL 链接 | 粘贴合同正文、上传 PDF 扫描件、给出在线合同链接 |
| C2 | 关键信息抽取 | 自动识别合同主体、标的额、期限、违约责任、争议解决条款等核心要素 | 从 30 页合同中提取签约方名称与付款节点 |
| C3 | 多维度风险扫描 | 从合规性、商业合理性、文本严谨性、程序完备性四个维度给出审查意见 | 识别"违约金比例畸高"或"缺少保密条款" |
| C4 | 结构化结果输出 | 按统一字段模板输出审查报告，支持 Markdown / JSON 两种格式 | 生成含风险等级、条款原文、修改建议的报告 |
| C5 | 置信度标注与复核 | 对每项审查结论标注置信度（高/中/低），低置信度项自动标记待核实 | 对模糊表述给出 `[需核实:签约主体资质]` 占位 |

### 1.2 不能做（明确边界）

| 序号 | 限制项 | 说明 |
|------|--------|------|
| N1 | 不提供正式法律意见 | 本工具输出仅为辅助参考，不替代执业律师出具的法律意见书 |
| N2 | 不保证审查完整性 | 受限于输入文本质量与模型能力，可能存在遗漏风险点 |
| N3 | 不处理非文本内容 | 图片中的合同内容需先经 OCR 转文本后方可分析 |
| N4 | 不执行合同修改 | 仅提供修改建议，不直接改动用户提供的原始文件 |
| N5 | 不存储用户数据 | 会话结束后不保留任何合同内容，请勿输入涉密信息 |

### 1.3 适用对象

- **适用**：企业法务、合同管理员、创业者、需要快速了解合同风险点的非法律专业人士
- **不适用**：需要出具具有法律效力的正式审查意见书的场景、涉及国家秘密或商业秘密的合同


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

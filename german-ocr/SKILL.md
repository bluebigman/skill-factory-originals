---
> 本内容由 AI 生成，仅供学习参考（《人工智能生成合成内容标识办法》显式标识）。
<!-- ai-generated-notice -->
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: german-ocr
name: german-ocr
displayName: 德语文档 票据识别 信息抽取
description: 从德文票据、表单、证件中自动提取关键字段，输出结构化数据。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/german-ocr
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 识文工作室
agent_created: true
trigger_words: ["发票识别", "德文OCR", "票据识别", "German OCR", "德文单据提取", "扫描件识别"]
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

# 德语文档识别与信息抽取（german-ocr）

## 一、能力边界与适用对象（速查卡）

本 Skill 面向需要从德文图像或 PDF 中提取结构化信息的场景。以下表格帮助你在 30 秒内判断是否适用。

| 维度 | 说明 |
|------|------|
| **核心用途** | 将德文票据、发票、表单、证件等扫描件或照片中的文字，转换为可检索、可处理的字段化数据 |
| **输入类型** | 图片（JPG/PNG/TIFF）、PDF 文件、可公开访问的图片 URL |
| **输出格式** | JSON 结构化数据，包含字段名、字段值、置信度分数 |
| **语言范围** | 德语为主，兼容部分英语混合内容（如国际化发票中的英文行） |
| **适用对象** | 财务人员、行政助理、物流专员、需要批量处理德文单据的运营团队 |

### 能做（核心能力）

1. **字段抽取**：从单据中提取日期、金额、发票号、税号、收款方、付款方等常见字段。
2. **版式适配**：支持横版、竖版、倾斜角度小于 15 度的扫描件；支持浅色背景上的深色文字。
3. **批量处理**：一次提交多张图片或一个多页 PDF，按顺序返回每页的独立结果。
4. **置信度标注**：每个字段附带 0~1 的置信度分数，低于阈值的字段会明确提示。
5. **自定义字段映射**：用户可在请求中指定需要额外提取的字段名（如 `bestellnummer` 订单号），系统按语义匹配尝试抽取。

### 不能做（明确边界）

| 限制项 | 说明 |
|--------|------|
| **手写体识别** | 仅支持印刷体；手写内容会标记为 `[需核实:手写内容]`，不猜测内容 |
| **复杂表格还原** | 不还原单元格坐标和表格结构，仅提取单元格内的文本值 |
| **多语言混合深度处理** | 非德语内容（如法语、波兰语）可能识别不完整，相关字段置信度会降低 |
| **图像修复** | 不提供去噪、去阴影、透视校正等图像预处理功能；图像质量过差时直接返回错误码 |
| **法律效力判定** | 不判断单据真伪，不提供法律合规建议 |


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

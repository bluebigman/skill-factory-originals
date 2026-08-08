---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: excel-image-extractor
name: excel-image-extractor
displayName: 表格图片 数据抽取 结构化输出
description: 从Excel表格及图片中抽取关键数据，按约定格式输出结构化结果。
version: 1.0.1
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/excel-image-extractor
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataCraft Studio
agent_created: true
trigger_words: ["Excel表格处理", "excel image extractor", "表格数据抽取", "图片转表格", "表格结构化"]

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

# Excel 图片数据抽取与表格处理 Skill 文档

## 一、能力边界速查卡

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入类型 | 用户直接粘贴的数据、上传的 Excel 文件（.xlsx/.xls）、图片文件（.png/.jpg）、可访问的 URL 链接 | 加密文件、损坏文件、需要登录鉴权的私有链接 |
| 数据处理 | 识别表格行列结构、提取单元格数值、保留表头信息、识别合并单元格、处理多 Sheet 工作簿 | 对图片中的手写内容进行高精度识别（仅支持印刷体）、执行复杂的公式计算 |
| 输出能力 | 生成 Markdown 表格、CSV 格式文本、JSON 结构化数据、按字段模板输出 | 直接修改用户本地文件（仅提供转换后的文本结果） |
| 批量处理 | 支持一次提交多个文件或 URL，按顺序逐一处理并汇总 | 并行处理超过 5 个文件（受上下文窗口限制） |
| 自定义能力 | 允许用户指定输出字段、调整列名映射、设置日期格式 | 自动推断用户未说明的业务规则（需明确告知） |

### 1.2 适用对象

- **数据分析师**：需要快速将截图或扫描件中的表格数据转为可编辑文本
- **行政人员**：整理报销单、签到表、库存清单等日常表格
- **开发者**：需要将 Excel 数据转为 JSON 供程序调用
- **学生研究者**：从文献附表中提取数据用于统计分析

### 1.3 输入输出规格

| 项目 | 规格说明 |
|------|----------|
| 输入来源 | 用户直接提供的数据文本、文件路径、URL 链接 |
| 输出格式 | 默认 Markdown 表格；可选 CSV、JSON（需用户指定） |
| 字段结构 | 保留原始表头，若表头缺失则自动生成 `列1`、`列2` 等占位名 |
| 置信度标注 | 对识别不确定的单元格标注 `[需核实:字段名]` |


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

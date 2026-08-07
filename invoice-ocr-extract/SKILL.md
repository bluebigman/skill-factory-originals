---
slug: invoice-ocr-extract
name: invoice-ocr-extract
displayName: 票据识别 字段提取 结构化输出
description: 从发票图片或PDF中提取关键字段，输出结构化表格，支持批量处理与置信度标注。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 独立技能工坊
agent_created: true
trigger_words: ["invoice-ocr-extract", "发票识别", "发票提取", "OCR发票", "发票结构化", "票据解析", "发票字段抽取"]
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

# 票据字段抽取与结构化输出指南

## 一、能力边界速查卡

| 维度 | 说明 |
|------|------|
| **核心能力** | 从发票图片或PDF中识别并提取关键字段（发票号码、开票日期、购买方信息、销售方信息、金额、税额、价税合计等），输出为结构化表格 |
| **支持格式** | JPG、PNG、PDF（单页或多页） |
| **批量处理** | 支持同一目录下多文件批量处理，自动生成汇总结果 |
| **置信度标注** | 每个字段附带识别置信度（高/中/低），低置信度字段自动标记 |
| **失败追踪** | 无法识别的文件单独记录失败原因，不中断整体流程 |

### 能做与不能做

**能做：**
- 标准版式发票（增值税普通发票、增值税专用发票）的字段提取
- 同一目录下批量处理，输出统一格式的表格
- 对识别结果进行置信度分级标注
- 生成失败明细清单，便于人工复核

**不能做：**
- 手写发票的准确识别（仅支持印刷体）
- 非发票类票据（如收据、行程单）的通用解析
- 对模糊、倾斜、反光严重的图片进行修复后再识别
- 自动验证发票真伪（需对接税务系统）

### 适用对象

- 财务人员：需要将纸质或电子发票信息录入系统
- 行政人员：处理报销单据时的信息登记
- 数据分析师：从大量发票中提取结构化数据用于分析


## 许可证（License）

```text
MIT License

Copyright (c) {year} {holder}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

```
<!-- professional-license-embedded -->

## 失败处理

- 命令执行失败或返回非零退出码时，程序会输出明确错误信息并给出排查建议。
- 依赖缺失时提示安装命令；网络异常时建议重试并检查连接。
- 异常情况不中断主流程，错误信息包含具体原因（error context），便于定位修复。
## 前置条件

- 本技能开箱即用，无需额外安装依赖。
- 需要 Python 3.9+ 运行环境。
- 涉及网络请求时需保持网络连通。
## 执行步骤

1. 读取输入参数或交互输入。
2. 按技能定义的处理流程执行核心逻辑。
3. 输出结构化结果，并在完成后给出下一步建议。
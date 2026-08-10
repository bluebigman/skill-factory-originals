---
slug: invoice-ocr-extract
name: invoice-ocr-extract
displayName: 票据识别 字段提取 结构化输出
description: 从发票图片或PDF中提取关键字段，输出结构化表格，支持批量处理与置信度标注。
version: 2.0.0
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

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


# 票据字段抽取与结构化输出工具

> 从发票图片或 PDF 中自动提取关键字段（发票号码、开票日期、买卖方信息、金额税额等），输出为结构化表格（CSV/JSON），支持批量处理、置信度标注与失败追踪。适用于财务录入、报销审核、数据分析等场景，帮助用户将纸质或电子发票信息快速数字化。

## 快速开始 Quick Start

以下是最短可用路径，帮助你快速上手：

| 场景 | 命令 | 预期结果 |
|------|------|----------|
| 单张发票图片识别 | `python run.py invoice.jpg` | 在终端打印提取的字段表格，并生成 `invoice_YYYYmmdd_HHMMSS.csv` 文件 |
| 批量识别目录下所有发票 | `python run.py ./invoices/ --batch` | 遍历 `./invoices/` 目录，为每个文件生成独立结果，并汇总为 `summary_YYYYmmdd_HHMMSS.csv` |
| 仅预览不写文件 | `python run.py invoice.pdf --dry-run` | 在终端打印将提取的字段与将写入的文件路径，不实际生成任何文件 |

## 适用场景 When to Use

**什么时候用：**
- 需要将纸质或电子发票信息录入财务系统
- 处理大量报销单据，需要快速登记信息
- 从发票数据中提取结构化信息用于数据分析
- 需要对识别结果进行置信度评估，以便人工复核

**什么时候不要用：**
- 手写发票（本工具仅支持印刷体）
- 非发票类票据（如收据、行程单、银行回单）
- 需要对模糊、倾斜、反光严重的图片进行修复后再识别（本工具不做图像增强）
- 需要验证发票真伪（需对接税务系统，本工具不提供）

## 能力总览 Capabilities

| 能力 | 命令/参数 | 示例 |
|------|-----------|------|
| 单文件识别 | `python run.py <file_path>` | `python run.py invoice.jpg` |
| 批量识别 | `python run.py <dir_path> --batch` | `python run.py ./invoices/ --batch` |
| 输出 JSON 格式 | `--format json` | `python run.py invoice.jpg --format json` |
| 预览模式（不写盘） | `--dry-run` | `python run.py invoice.jpg --dry-run` |
| 详细日志 | `--verbose` | `python run.py invoice.jpg --verbose` |
| 自检测试 | `--selftest` | `python run.py --selftest` |
| 指定输出目录 | `--output-dir <dir>` | `python run.py invoice.jpg --output-dir ./results/` |

## 模块决策表 Decision Table

| 用户意图 | 推荐模块/命令 | 读取指引 |
|----------|---------------|----------|
| 识别单张发票 | `python run.py <file>` | 直接执行，结果打印在终端并写入 CSV |
| 批量处理整个文件夹 | `python run.py <dir> --batch` | 自动遍历目录，生成汇总文件 |
| 需要 JSON 格式结果 | `python run.py <file> --format json` | 输出 JSON 文件，便于程序化处理 |
| 只想预览不生成文件 | `python run.py <file> --dry-run` | 打印提取结果与将写入的路径 |
| 排查识别问题 | `python run.py <file> --verbose` | 输出详细日志，包含每个字段的匹配过程 |
| 验证工具是否正常 | `python run.py --selftest` | 运行内置测试，断言关键输出 |

## 示例 Examples

### 示例 1：单张发票识别

**输入：**

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

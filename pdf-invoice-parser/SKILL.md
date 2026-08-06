---
slug: pdf-invoice-parser
name: pdf-invoice-parser
displayName: PDF发票解析与一致性校验
description: 从PDF发票中提取结构化字段并校验数据一致性，支持批量处理与多格式输出。
version: 3.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 数据工坊
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据工坊
agent_created: true
trigger_words: ["pdf-invoice-parser", "发票解析", "提取发票信息", "PDF发票转数据", "invoice extraction", "票据识别", "发票数据化"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# PDF发票解析与一致性校验

## 能力边界

### 能做
- 从PDF发票中提取结构化字段（发票代码、号码、日期、买卖方信息、金额、税额、价税合计、税率、备注）
- 支持单文件、目录批量、HTTP/HTTPS远程链接输入
- 双引擎文本提取（pdfplumber优先，pypdf降级）
- 四项一致性校验：金额+税额=价税合计、大小写金额一致、号码位数合法、日期格式合法
- 输出JSON/JSONL/CSV格式
- 内置自检功能（--selftest）

### 不能做
- 图片格式（JPG/PNG）直接解析（需先转PDF）
- 手写体发票、模糊扫描件
- 与税务系统实时联网核验真伪
- 非中文发票（如英文、日文）
- 超过10MB或超过50页的超大文件

## 触发条件

- 用户提供PDF发票文件路径、目录路径或HTTP/HTTPS链接
- 用户要求提取发票信息、解析发票、发票数据化
- 用户要求校验发票数据一致性

## 标准流程

1. **输入处理**：接收文件路径/目录/URL
2. **PDF验证**：检查文件存在性、PDF魔数、加密状态
3. **文本提取**：尝试pdfplumber，失败降级pypdf
4. **字段解析**：基于正则表达式提取关键字段
5. **一致性校验**：执行四项校验规则
6. **结果输出**：按指定格式输出JSON/JSONL/CSV

## 置信度门控

- 文本提取成功但未识别出发票关键字段 → 返回E006错误
- 金额字段解析失败 → 返回E007错误
- 一致性校验未通过 → 返回E008错误（但保留解析结果）

## 错误码

| 错误码 | 含义 |
|--------|------|
| E001 | 输入路径不存在或不可读 |
| E002 | 文件不是有效PDF（魔数校验失败） |
| E003 | PDF已加密，需要口令 |
| E004 | PDF无文本层且OCR依赖未安装 |
| E005 | 未安装任何PDF解析引擎 |
| E006 | 文本提取成功但未识别出发票关键字段 |
| E007 | 金额字段解析失败 |
| E008 | 一致性校验未通过 |
| E009 | 批量目录未找到任何PDF |
| E010 | 输出写入失败 |

## FAQ与反模式

### FAQ
- **Q: 如何处理扫描件？** A: 当前版本不支持OCR，需先使用OCR工具将扫描件转为可搜索PDF。
- **Q: 支持哪些发票类型？** A: 中国增值税电子发票、专用发票、数电票。
- **Q: 如何批量处理？** A: 传入目录路径，自动处理目录下所有PDF文件。

### 反模式
- ❌ 不要用随机数据伪造解析结果
- ❌ 不要忽略一致性校验失败
- ❌ 不要在没有PDF解析引擎时静默失败
- ❌ 不要对网络请求不设超时

## 许可证

MIT License

Copyright (c) 2024 数据工坊

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
## 失败处理

- 命令执行失败或返回非零退出码时，程序会输出明确错误信息并给出排查建议。
- 依赖缺失时提示安装命令；网络异常时建议重试并检查连接。
- 异常情况不中断主流程，错误信息包含具体原因（error context），便于定位修复。
## 前置条件

- 本技能开箱即用，无需额外安装依赖。
- 需要 Python 3.9+ 运行环境。
- 涉及网络请求时需保持网络连通。
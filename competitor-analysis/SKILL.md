---
name: competitor-analysis
description: 竞品数据多维对比分析，输出功能/定价/评价对比与差异化建议报告
version: 2.0.0
license: MIT
ai_generated: true
disclaimer: true
source_project: skill-factory-originals
copyright_holder: bluebigman

---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


# competitor-analysis

竞品数据多维对比分析工具。读取多个竞品的数据文件（CSV/JSON/Markdown/TXT），输出功能、定价、评价三个维度的对比结果，并生成差异化建议报告。

## 能力边界

**能做**：
- 读取 CSV、JSON、Markdown 表格、TXT 四种格式的竞品数据文件
- 自动识别数据中的功能、定价、评价字段并提取
- 输出结构化对比报告（JSON 格式）和人类可读摘要（控制台）
- 对缺失字段、格式错误的数据进行容错处理并记录错误明细
- 支持自定义输出目录和文件名前缀

**不能做**：
- 不自动抓取网络数据（需用户自行准备数据文件）
- 不进行情感分析或语义理解（仅做字段提取和统计）
- 不生成图表或可视化（仅输出文本报告）
- 不保证对加密、损坏或非标准格式文件的处理结果

**不适用**：
- 涉及重大商业决策时，请以官方原始数据为准，本工具输出仅供效率参考

## 触发条件

- 用户提供至少一个竞品数据文件（CSV/JSON/MD/TXT）
- 用户要求进行竞品对比分析
- 用户输入关键词：竞品分析、竞品对比、市场对标、差异化分析

## 标准流程

### 1. 准备输入
- 将竞品数据文件放入同一目录
- 文件名建议格式：`竞品名_其他描述.csv`（下划线前部分作为竞品名）

### 2. 执行分析

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
---
slug: data-visual-report
name: data-visual-report
displayName: 数据洞察 图表报告 自动生成
description: 将表格数据自动转换为带图表与结论的可视化分析报告
version: 2.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: DataCraft Studio
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataCraft Studio
agent_created: true
trigger_words: ["数据可视化", "图表报告", "趋势分析", "占比统计", "TopN排行", "可视化分析", "数据报告", "图表生成"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


# 数据洞察 · 图表报告自动生成 Skill

> **一句话定位**：将 CSV/JSON 表格数据自动转换为带图表与结论的可视化分析报告（HTML + Markdown），为业务分析师、项目经理、学术研究者提供开箱即用的数据看板生成工具。

---

## 快速开始 Quick Start

| 场景 | 命令 | 预期结果 |
|------|------|----------|
| 生成完整报告 | `python run.py input.csv -o report.html` | 生成包含图表与结论的 HTML 报告 |
| 仅查看统计摘要 | `python run.py input.csv --summary` | 终端输出统计指标（均值/中位数/极值等） |
| 预览不写盘 | `python run.py input.csv --dry-run` | 打印将生成的报告路径与内容摘要，不写文件 |

---

## 适用场景 When to Use

### ✅ 什么时候用
- 需要快速生成数据看板的业务分析师
- 需要将数据结果汇报给非技术团队的项目经理
- 需要为论文/报告补充图表的学术研究者
- 需要验证数据分布规律的数据科学初学者

### ❌ 什么时候不要用
- 输入为纯文本、图片、PDF 中的非结构化表格
- 需要跨表 JOIN 或数据库实时查询
- 需要自定义图表样式/配色/布局
- 数据量超过 10,000 行或文件超过 100MB

---

## 能力总览 Capabilities

| 能力项 | 命令/参数 | 示例 | 说明 |
|--------|-----------|------|------|
| 表格数据读取 | `run.py input.csv` / `run.py input.json` | `python run.py data.csv` | 支持 CSV/JSON，自动编码检测（utf-8/gbk/gb18030） |
| 统计指标计算 | `--summary` | `python run.py data.csv --summary` | 均值/中位数/标准差/极值/缺失值统计 |
| 图表自动生成 | 默认开启 | `python run.py data.csv -o report.html` | 折线图/柱状图/饼图（Chart.js） |
| 趋势分析 | 自动识别时间字段 | `python run.py sales.csv` | 识别上升/下降/波动模式 |
| 占比统计 | 自动识别分类字段 | `python run.py categories.csv` | 计算分类占比并生成饼图 |
| TopN 排行 | `--top-n 10` | `python run.py data.csv --top-n 5` | 提取数值字段前 N 名 |
| 结论生成 | 默认开启 | `python run.py data.csv` | 基于统计结果自动撰写分析结论 |
| Markdown 报告 | `--format md` | `python run.py data.csv --format md` | 输出 Markdown 格式报告 |
| 预览模式 | `--dry-run` | `python run.py data.csv --dry-run` | 只打印摘要不写盘 |
| 自检模式 | `--selftest` | `python run.py --selftest` | 运行内置测试并断言关键输出 |

---

## 模块决策表 Decision Table

| 用户意图 | 推荐模块 | 命令示例 | 读取指引 |
|----------|----------|----------|----------|
| 快速看数据分布 | 统计摘要 | `python run.py data.csv --summary` | 查看终端输出的均值/中位数/极值 |
| 生成汇报图表 | 图表报告 | `python run.py data.csv -o report.html` | 用浏览器打开生成的 HTML 文件 |
| 分析时间趋势 | 趋势分析 | `python run.py sales.csv` | 查看报告中的趋势结论段落 |
| 查看分类占比 | 占比统计 | `python run.py categories.csv` | 查看报告中的饼图与占比表格 |
| 提取关键排行 | TopN 排行 | `python run.py data.csv --top-n 5` | 查看报告中的 TopN 表格 |
| 预览报告内容 | 预览模式 | `python run.py data.csv --dry-run` | 查看终端输出的报告摘要 |

---

## 示例 Examples

### 示例 1：生成完整 HTML 报告

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

---
slug: data-visual-report
name: data-visual-report
displayName: 数据洞察 图表报告 自动生成
description: 将表格数据自动转换为带图表与结论的可视化分析报告
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataCraft Studio
agent_created: true
trigger_words: ["数据可视化", "图表报告", "趋势分析", "占比统计", "TopN排行", "可视化分析", "数据报告", "图表生成"]
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

# 数据洞察 · 图表报告自动生成 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入要求 |
|--------|------|----------|
| 表格数据读取 | 解析 CSV / Excel / JSON 格式的结构化数据 | 文件 ≤ 5MB，行数 ≤ 10,000 行 |
| 图表自动生成 | 根据字段类型自动匹配折线图、柱状图、饼图 | 至少 1 列分类/时间字段 + 1 列数值字段 |
| 趋势分析 | 识别时间序列的上升/下降/波动模式 | 时间字段格式需为日期或连续序号 |
| 占比统计 | 计算分类字段的数值占比并生成饼图 | 分类字段去重后 ≤ 20 个类别 |
| TopN 排行 | 提取数值字段的前 N 名（默认 Top 10） | 数值字段为可排序的数值类型 |
| 结论生成 | 基于统计结果自动撰写分析结论 | 数据量 ≥ 3 行，否则仅做描述性说明 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 非结构化数据 | 无法处理纯文本、图片、PDF 中的表格 |
| 缺失值处理 | 不做插补，仅标注 [需核实:字段名] 并跳过该行 |
| 因果推断 | 只做相关性描述，不推断因果关系 |
| 实时数据 | 仅处理用户提供的静态文件，不连接数据库或 API |
| 多表关联 | 仅支持单文件单表，不支持跨表 JOIN |
| 自定义图表样式 | 输出固定模板样式，不提供个性化配色/布局定制 |

### 1.3 适用对象

- 需要快速生成数据看板的业务分析师
- 需要将数据结果汇报给非技术团队的项目经理
- 需要为论文/报告补充图表的学术研究者
- 需要验证数据分布规律的数据科学初学者


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

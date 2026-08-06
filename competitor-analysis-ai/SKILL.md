---
slug: competitor-analysis-ai
name: competitor-analysis
displayName: 竞品拆解 策略对比 市场洞察
description: 多维度拆解竞品，输出可执行差异化策略与结构化对比报告。
version: 3.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨研
agent_created: true
trigger_words: ["competitor-analysis", "竞品分析", "竞品对比", "竞争策略", "市场分析", "竞品拆解", "差异化定位", "竞争情报"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。

# 竞品拆解与差异化策略生成 Skill

## 一、能力边界：一页纸速查卡

### 1.1 能做与不能做

| 维度 | ✅ 能做 | ❌ 不能做 |
|------|--------|----------|
| **数据输入** | 接受结构化 JSON 文件、命令行参数传入的竞品数据、URL 数据源（JSON 格式） | 无法自动爬取网页数据，需用户自行准备素材 |
| **分析维度** | 功能、定价、用户体验、市场定位、技术架构、运营策略（基于输入数据） | 无法进行真实用户访谈或实地调研 |
| **输出形式** | 结构化 JSON 对比报告、差异化策略建议、风险提示、CSV 导出 | 无法保证策略落地效果，不提供执行资源 |
| **数据校验** | 对缺失字段标注 `[需核实:字段名]` 占位；对无效数据报错 | 不编造数据，不猜测未提供的信息 |
| **批量处理** | 支持多竞品并行分析（建议 ≤ 10 个） | 超过 10 个时输出质量下降，建议分批 |
| **网络请求** | 支持从 URL 获取竞品数据（带超时与指数退避重试） | 不进行无限制的爬取，仅支持 JSON 数据源 |

### 1.2 适用对象

| 适用场景 | 不适用场景 |
|----------|-----------|
| 产品经理做季度竞品调研 | 需要实时数据监控的持续性分析 |
| 创业团队评估市场进入策略 | 需要财务级精度的估值对比 |
| 市场部制定差异化传播方案 | 需要法律合规审查的深度分析 |
| 运营团队优化用户留存策略 | 需要用户画像细分的定量研究 |

## 二、触发条件

### 2.1 触发词

以下任一关键词出现在用户输入中即触发本 Skill：
- `competitor-analysis`
- `竞品分析`
- `竞品对比`
- `竞争策略`
- `市场分析`
- `竞品拆解`
- `差异化定位`
- `竞争情报`

### 2.2 触发示例

用户输入："帮我做一份竞品分析报告" → 触发本 Skill。

## 三、标准流程

### 3.1 输入准备

1. 用户提供竞品数据，支持以下三种方式（可组合使用）：
   - **文件路径**：`--file path/to/data.json`
   - **URL**：`--url https://example.com/data.json`
   - **命令行参数**：`--data '{"competitors": [...]}'`
2. 数据格式要求（JSON）：

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
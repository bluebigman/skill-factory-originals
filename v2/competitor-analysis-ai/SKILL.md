---
slug: competitor-analysis-ai
name: competitor-analysis
displayName: 竞品拆解 策略对比 市场洞察
description: 多维度拆解竞品，输出可执行差异化策略与结构化对比报告。
version: 2.0.0
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

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


# 竞品拆解与差异化策略生成 Skill

> 一句话定位：面向产品经理、创业团队与市场运营，将零散的竞品信息转化为结构化对比报告与可执行的差异化策略建议。

## 快速开始 Quick Start

| 场景 | 命令 | 预期结果 |
|------|------|----------|
| 分析内置示例数据 | `python run.py --demo` | 输出 3 个竞品的完整分析报告（JSON 格式） |
| 分析自定义 JSON 文件 | `python run.py --input data.json` | 从文件读取竞品数据并输出分析报告 |
| 从 URL 拉取数据 | `python run.py --url https://example.com/data.json` | 带重试机制的网络请求，成功后输出分析报告 |
| 导出 CSV 对比表 | `python run.py --input data.json --export report.csv` | 生成 CSV 文件，可用 Excel 打开 |
| 自检功能 | `python run.py --selftest` | 运行内置测试用例，全部通过返回退出码 0 |

## 适用场景 When to Use

### ✅ 推荐使用
- 产品经理做季度竞品调研，需要快速梳理竞品功能与定价
- 创业团队评估市场进入策略，分析头部玩家优劣势
- 市场部制定差异化传播方案，需要竞品定位对比
- 运营团队优化用户留存策略，参考竞品运营手段

### ❌ 不要使用
- 需要实时数据监控的持续性分析（本工具是快照式分析）
- 需要财务级精度的估值对比（本工具不提供财务模型）
- 需要法律合规审查的深度分析（请咨询专业律师）
- 需要用户画像细分的定量研究（本工具不采集用户数据）

## 能力总览 Capabilities

| 能力 | 命令/参数 | 示例 |
|------|-----------|------|
| 从文件加载数据 | `--input <path>` | `--input competitors.json` |
| 从 URL 加载数据 | `--url <url>` | `--url https://api.example.com/data` |
| 使用内置示例 | `--demo` | `--demo` |
| 导出 CSV 报告 | `--export <path>` | `--export report.csv` |
| 指定输出目录 | `--output-dir <dir>` | `--output-dir ./results` |
| 详细模式 | `--verbose` | `--verbose` |
| 预览模式 | `--dry-run` | `--dry-run`（不写盘，只打印将执行的操作） |
| 自测试 | `--selftest` | `--selftest` |
| 显示版本 | `--version` | `--version` |

## 模块决策表 Decision Table

| 用户意图 | 推荐模块 | 读取指引 |
|----------|----------|----------|
| 快速了解工具能力 | `--demo` | 查看内置示例输出，理解报告结构 |
| 分析自有数据 | `--input` | 准备 JSON 格式数据，参考 `spec.json` 中的字段定义 |
| 从网页获取数据 | `--url` | 确保 URL 可公开访问，支持 HTTPS |
| 需要 Excel 格式 | `--export` | 导出后可用 Excel/WPS 打开 |
| 批量处理多个文件 | 多次调用 `--input` | 每次处理一个文件，结果独立输出 |
| 验证工具是否正常 | `--selftest` | 运行内置测试，检查退出码是否为 0 |

## 示例 Examples

### 示例 1：分析内置示例数据

```bash
python run.py --demo
```

输出（节选）：
```json
{
  "report": {
    "generated_at": "2026-08-09T12:00:00+00:00",
    "competitors": [
      {
        "name": "示例产品A",
        "features_score": 8,
        "pricing_score": 6,
        "ux_score": 7,
        "positioning_score": 8,
        "tech_stack_score": 7,
        "operations_score": 6,
        "overall_score": 7.0
      }
    ]
  }
}
```

### 示例 2：分析自定义 JSON 文件

```bash
python run.py --input my_competitors.json --verbose
```

输入文件格式：
```json
[
  {
    "name": "竞品A",
    "features": ["功能1", "功能2"],
    "pricing": "免费",
    "ux": "简洁",
    "positioning": "高端",
    "tech_stack": ["Python", "React"],
    "operations": "社区运营"
  }
]
```

### 示例 3：导出 CSV 报告

```bash
python run.py --input data.json --export report.csv --output-dir ./results
```

生成 `./results/report.csv`，包含各维度评分与总分。

## 安装与配置 Installation

### 环境要求
- Python 3.9+
- 无需第三方依赖（仅使用标准库）

### 安装步骤

```bash
# 克隆或下载 Skill 文件
# 确保 run.py 和 spec.json 在同一目录
# 赋予执行权限（可选）
chmod +x run.py
```

### 数据格式说明

输入数据为 JSON 数组，每个元素代表一个竞品，支持字段：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | ✅ | 竞品名称 |
| `features` | array | ❌ | 功能列表 |
| `pricing` | string | ❌ | 定价策略 |
| `ux` | string | ❌ | 用户体验描述 |
| `positioning` | string | ❌ | 市场定位 |
| `tech_stack` | array | ❌ | 技术栈 |
| `operations` | string | ❌ | 运营策略 |

## 常见问题 Troubleshooting

| 错误现象 | 原因 | 解决办法 |
|----------|------|----------|
| `文件不存在 (错误码 3)` | 输入路径错误 | 检查文件路径，使用绝对路径 |
| `URL 请求失败 (错误码 4)` | 网络问题或 URL 无效 | 检查网络连接，确认 URL 可访问 |
| `数据格式错误 (错误码 2)` | JSON 格式不正确 | 使用 `python -m json.tool data.json` 校验格式 |
| `输出目录无法创建 (错误码 5)` | 权限不足 | 更换目录或检查权限 |
| 中文乱码 | 编码问题 | 确保文件为 UTF-8 编码 |

## 最佳实践 Best Practices

### 数据准备
- 每个竞品至少提供 `name` 字段
- 尽量填写所有维度字段，缺失字段会标记 `[需核实]`
- 建议一次分析不超过 10 个竞品，保证输出质量

### 结果解读
- 评分范围为 1-10 分，基于规则引擎计算
- 差异化策略建议基于评分差异自动生成
- 风险提示基于缺失字段和低分维度

### 安全提醒
- 不要将敏感商业数据写入公开 URL
- 分析结果仅供内部参考，不构成投资建议
- 涉及法律/财务决策请咨询专业人士

## 相关资源 Related

- [JSON 格式说明](https://www.json.org/json-zh.html)
- [Python 官方文档](https://docs.python.org/3/)
- [Markdown 语法参考](https://www.markdownguide.org/)

---

## 能力边界：一页纸速查卡

### 能做与不能做

| 维度 | ✅ 能做 | ❌ 不能做 |
|------|--------|----------|
| **数据输入** | 接受 JSON 文件、URL、内置示例 | 无法自动爬取网页数据，需用户自行准备素材 |
| **分析维度** | 功能、定价、用户体验、市场定位、技术架构、运营策略 | 无法进行真实用户访谈或实地调研 |
| **输出形式** | 结构化对比报告（JSON/CSV）、差异化策略建议、风险提示 | 无法保证策略落地效果，不提供执行资源 |
| **数据校验** | 对缺失字段标注 `[需核实:字段名]` 占位 | 不编造数据，不猜测未提供的信息 |
| **批量处理** | 支持多竞品并行分析（建议 ≤ 10 个） | 超过 10 个时输出质量下降，建议分批 |

### 评分规则说明

评分基于规则引擎，对每个维度进行 1-10 分评估：
- **功能 (features)**：功能数量与完整性
- **定价 (pricing)**：价格竞争力
- **用户体验 (ux)**：描述中的正面关键词
- **市场定位 (positioning)**：定位清晰度
- **技术栈 (tech_stack)**：技术先进性
- **运营 (operations)**：运营策略丰富度

总分 = 各维度平均分（保留一位小数）。

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

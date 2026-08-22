---
slug: pretzelai
name: pretzelai
displayName: 数据洞察 可视化分析 智能报告
description: 将数据、文件或URL转化为结构化洞察与可视化结果。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingDataWorks
agent_created: true
trigger_words: ["数据可视化", "pretzelai", "Jupyter替代", "数据分析", "交互式笔记本", "数据洞察", "图表生成", "报告生成"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# PretzelAI 技能文档

## 一、能力边界速查卡

### 1.1 能做什么

| 能力项 | 说明 | 输入示例 | 输出示例 |
|--------|------|----------|----------|
| 文件解析 | 读取 CSV、JSON、Excel、TXT 等常见格式 | `sales_2024.csv` | 结构化数据表 + 字段统计 |
| URL 抓取 | 从公开网页提取表格或列表数据 | `https://example.com/data` | 清洗后的数据集 |
| 单样本分析 | 对一份数据执行完整分析流水线 | 任意单文件 | 分析报告（含图表） |
| 批量处理 | 对多份同构数据执行相同分析逻辑 | 文件夹内 20 个 CSV | 汇总对比报告 |
| 可视化生成 | 自动选择图表类型并渲染 | 数值型列 × 2 | 散点图 / 折线图 |
| 报告导出 | 生成 Markdown 或 HTML 格式报告 | 分析结果对象 | `report.md` / `report.html` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 非结构化文本深度理解 | 不擅长长文语义分析（如合同条款、法律文书），仅支持表格类数据提取 |
| 实时流数据处理 | 不支持 Kafka、WebSocket 等实时数据源接入 |
| 自定义机器学习模型训练 | 仅提供基础统计与回归分析，不包含深度学习训练能力 |
| 私有协议数据库直连 | 不支持 Oracle、SAP HANA 等专有协议的直连查询 |
| 图像/音频内容识别 | 不支持从图片或音频中提取数据 |

### 1.3 适用对象

- **数据分析师**：需要快速探索数据分布与趋势
- **产品经理**：需要将用户行为数据转化为可视化看板
- **运营人员**：需要定期生成业务周报/月报
- **开发者**：需要将数据洞察集成到自动化流水线

---

## 二、触发方式与场景映射

### 2.1 触发词

直接使用以下任一词汇即可激活本技能：

- 数据可视化
- pretzelai
- Jupyter替代
- 数据分析
- 交互式笔记本
- 数据洞察
- 图表生成
- 报告生成

### 2.2 场景映射表

| 用户说（大白话） | 技能执行动作 |
|------------------|--------------|
| "帮我看下这个 CSV 里有什么规律" | 执行单样本分析，输出统计摘要 + 自动图表 |
| "把这三个 Excel 合并对比一下" | 执行批量处理，输出对比报告 |
| "这个网页里的表格能抓下来吗" | 执行 URL 抓取 + 数据清洗 |
| "我想每周自动出一份销售报告" | 指导配置 CI/CD 定时任务 |
| "图表样式能改吗" | 传入 matplotlib 样式表参数 |

---

## 三、标准工作流

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 输入数据 | 文件大小 ≤ 50MB；列数 ≤ 200；行数 ≤ 100 万 | 文件属性 / 命令行 `wc -l` |
| 运行环境 | Python 3.9+；已安装 `pretzelai` 包 | `pip show pretzelai` |
| 网络（仅 URL 场景） | 目标 URL 可公开访问，无登录墙 | `curl -I <url>` 返回 200 |
| 依赖库 | pandas ≥ 2.0, matplotlib ≥ 3.5 | `pip list \| grep pandas` |

### 3.2 执行步骤

#### Step 1：确认需求匹配

阅读「能力边界速查卡」，确认你的需求在「能做什么」范围内。若在「不能做什么」列表中，直接终止流程并告知用户。

#### Step 2：运行单样本分析

```bash
# 基本用法
pretzelai analyze --input ./data/sales.csv --output ./report/

# 指定图表样式
pretzelai analyze --input ./data/sales.csv --output ./report/ --style ggplot

# 自定义输出模板（JSON Schema）
pretzelai analyze --input ./data/sales.csv --output ./report/ --schema ./custom_schema.json
```

**参数说明：**

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | 是 | 无 | 输入文件路径或 URL |
| `--output` | 是 | 无 | 输出目录 |
| `--style` | 否 | `default` | matplotlib 样式表名称 |
| `--schema` | 否 | 内置模板 | 自定义 JSON Schema 路径 |
| `--batch` | 否 | 关闭 | 批量模式开关 |
| `--selftest` | 否 | 关闭 | 运行自检 |
| `--version` | 否 | 关闭 | 显示版本号 |

#### Step 3：查看输出报告

输出目录将包含：

```
report/
├── summary.md          # 数据摘要（行数、列数、缺失值、数据类型）
├── charts/
│   ├── distribution.png  # 数值列分布直方图
│   ├── correlation.png   # 相关性热力图
│   └── trend.png         # 时间趋势图（若存在时间列）
└── insights.json       # 结构化洞察结果
```

**`insights.json` 字段说明：**

| 字段 | 类型 | 含义 |
|------|------|------|
| `row_count` | int | 数据行数 |
| `column_count` | int | 数据列数 |
| `missing_rate` | float | 整体缺失率（0-1） |
| `top_correlations` | array | 相关性最高的前 5 对特征 |
| `outlier_columns` | array | 检测到异常值的列名列表 |
| `recommended_charts` | array | 建议的图表类型列表 |

#### Step 4：批量运行

```bash
pretzelai analyze --input ./data_folder/ --output ./batch_report/ --batch
```

批量模式要求文件夹内所有文件具有相同的列结构。输出将包含：

- 每个文件的独立报告
- `comparison_summary.md`：跨文件对比摘要

#### Step 5：抽检验证

从输出中随机抽取 3-5 个数据点，与原始数据交叉核对，确认分析结果无系统性偏差。

### 3.3 输出规范

- 所有报告使用 UTF-8 编码
- 图表分辨率为 150 DPI，PNG 格式
- 数值保留 4 位小数
- 缺失值以 `null` 表示，不填充猜测值

---

## 四、置信度门控

当遇到以下情况时，**不得编造数据**，必须输出 `[需核实:字段名]` 占位符：

| 场景 | 处理方式 |
|------|----------|
| 数据列含义不明确 | 在报告中标注 `[需核实:列名含义]` |
| 缺失率 > 30% 的列 | 标注 `[需核实:高缺失率列]`，不参与统计推断 |
| URL 抓取失败 | 返回错误码 `E1003`，不猜测内容 |
| 批量文件中列结构不一致 | 跳过该文件，标注 `[需核实:文件结构]` |
| 相关性计算样本量 < 30 | 标注 `[需核实:样本量不足]`，不输出相关系数 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E1001` | 文件格式不支持 | "无法解析该文件格式，支持 CSV/JSON/Excel/TXT" | 转换格式后重试 |
| `E1002` | 文件大小超限 | "文件超过 50MB 限制，请拆分后重试" | 使用 `split` 命令拆分 |
| `E1003` | URL 无法访问 | "目标 URL 返回非 200 状态码，请检查链接" | 确认链接可公开访问 |
| `E1004` | 列结构不一致 | "批量模式下所有文件必须具有相同列结构" | 统一列名后重试 |
| `E1005` | 内存不足 | "数据量过大导致内存溢出，请减少行数或分块处理" | 使用 `--chunk-size` 参数 |
| `E1006` | 图表渲染失败 | "matplotlib 样式表不存在，回退到默认样式" | 检查样式表名称 |
| `E1007` | 输出目录无权限 | "无法写入输出目录，请检查权限" | 修改目录权限或更换路径 |

---

## 六、FAQ 反模式对照

### 常见坑 1：忽略数据清洗直接分析

**错误做法**：直接对含大量缺失值的数据执行分析，导致图表失真。

**正确做法**：先查看 `summary.md` 中的缺失率，对高缺失列单独处理或标注。

### 常见坑 2：批量模式混入异构文件

**错误做法**：将不同结构的 CSV 放在同一文件夹批量运行，导致大量 `E1004` 错误。

**正确做法**：按列结构分文件夹存放，或先运行单样本确认结构一致。

### 常见坑 3：URL 抓取未检查反爬机制

**错误做法**：直接抓取有反爬限制的网站，得到空数据。

**正确做法**：先用 `curl -I` 检查响应头，确认无 `403` 或验证码。

### 常见坑 4：过度解读相关性

**错误做法**：看到高相关系数就断言因果关系。

**正确做法**：在报告中注明"相关性不代表因果性"，并建议进一步实验验证。

### 常见坑 5：忽略输出模板自定义

**错误做法**：每次都使用默认模板，导致报告格式与团队规范不符。

**正确做法**：编写一次自定义 JSON Schema，后续通过 `--schema` 参数复用。

---

## 七、渐进式披露阅读路径

### 新手路径（5 分钟上手）

1. 阅读「能力边界速查卡」→ 确认需求匹配
2. 阅读「标准工作流」Step 1-3 → 完成第一次单样本分析
3. 查看输出报告 → 理解 `summary.md` 和 `insights.json` 字段含义
4. 遇到问题 → 查「错误码体系」对照表

### 进阶路径（深度使用）

1. 阅读「触发方式与场景映射」→ 掌握批量与定时场景
2. 阅读「标准工作流」Step 4-5 → 配置批量流水线
3. 自定义输出模板 → 修改 JSON Schema 适配团队规范
4. 集成 CI/CD → 使用 `--batch` 参数配置定时任务
5. 优化图表 → 传入自定义 matplotlib 样式表

---

## 八、扩展指南

### 8.1 自定义输出模板

创建 `custom_schema.json`：

```json
{
  "report_title": "月度销售分析",
  "include_sections": ["summary", "charts", "insights"],
  "chart_config": {
    "figsize": [12, 6],
    "dpi": 200,
    "color_palette": "viridis"
  },
  "insights_columns": ["row_count", "missing_rate", "top_correlations"]
}
```

### 8.2 集成 CI/CD 流水线

```yaml
# .github/workflows/data-report.yml
name: Weekly Data Report
on:
  schedule:
    - cron: "0 9 * * 1"  # 每周一上午 9 点
jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install pretzelai
      - run: pretzelai analyze --input ./data/ --output ./report/ --batch
      - uses: actions/upload-artifact@v4
        with:
          name: weekly-report
          path: ./report/
```

### 8.3 扩展数据源

在 `~/.pretzelai/parsers/` 目录下添加自定义解析器：

```python
# custom_parser.py
def parse(file_path):
    # 自定义解析逻辑
    return dataframe
```

### 8.4 优化图表样式

使用内置样式或自定义样式表：

```bash
pretzelai analyze --input data.csv --output report/ --style seaborn-v0_8-darkgrid
```

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应自行承担因使用本 Skill 产生的全部责任。包括但不限于因数据分析结果不准确、数据泄露、决策失误等造成的直接或间接损失。

2. **禁止反向工程**：未经明确书面许可，不得对本 Skill 的底层算法、提示词结构、决策逻辑进行反向工程、反编译或提取核心逻辑用于商业用途。

3. **合规使用**：使用者应遵守所在地法律法规，不得将本 Skill 用于任何非法目的，包括但不限于未经授权的数据抓取、隐私侵犯、欺诈行为等。

4. **免责声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权保证。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 LingDataWorks

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

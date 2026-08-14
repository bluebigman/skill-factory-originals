---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: pretzelai
name: pretzelai
displayName: 数据洞察 可视化分析 智能转化
description: 将数据、文件或URL转化为结构化洞察与可视化结果。
version: 1.0.2
rules_version: cpr-20260814-n426
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/pretzelai
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingData Studio
agent_created: true
trigger_words: ["数据可视化", "pretzelai", "Jupyter替代", "数据分析", "交互式笔记本", "数据洞察", "图表生成", "报表分析"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# PretzelAI 技能手册：数据到洞察的转化工作流

## 一、能力边界：一页纸速查卡

### 1.1 能做什么（In-Scope）

| 能力项 | 说明 | 典型场景 |
|--------|------|----------|
| 文件数据解析 | 读取 CSV、Excel、JSON、Parquet 等格式文件 | 销售报表、用户行为日志 |
| URL 数据抓取 | 从公开网页或 API 端点提取结构化数据 | 行业指数、公开数据集 |
| 数据清洗与预处理 | 缺失值处理、类型转换、去重 | 合并多来源数据前 |
| 探索性分析 | 描述性统计、相关性矩阵、分布检测 | 理解数据全貌 |
| 可视化生成 | 生成静态图表（matplotlib/plotly） | 汇报材料、趋势展示 |
| 结构化洞察输出 | 生成 Markdown 报告或 JSON 摘要 | 自动周报、数据简报 |

### 1.2 不能做什么（Out-of-Scope）

- 不能访问需要身份验证的私有数据库或内网服务
- 不能执行实时流式数据处理（仅支持批处理）
- 不能生成交互式仪表盘（仅静态图表）
- 不能处理超过 2GB 的单个文件（内存限制）
- 不能对图片/PDF 中的非结构化文本做 OCR 识别

### 1.3 适用对象

- 需要快速理解数据结构的业务分析师
- 需要自动化生成数据报告的数据工程师
- 需要替代 Jupyter 轻量级探索的数据科学初学者
- 需要将 URL 数据转为本地结构化文件的爬虫使用者

---

## 二、触发方式：场景映射表

| 用户说（大白话） | 触发词匹配 | 实际动作 |
|------------------|------------|----------|
| "帮我把这个 CSV 画成图" | 数据可视化 | 解析文件 → 生成图表 → 输出 PNG |
| "分析一下这个网页里的表格" | URL 数据抓取 | 抓取 URL → 提取表格 → 结构化输出 |
| "这个数据有什么规律" | 数据分析 | 执行描述性统计 → 输出洞察摘要 |
| "我不想开 Jupyter，快速看下数据" | Jupyter替代 | 启动轻量分析流程 → 输出 Markdown 报告 |
| "把这几列做个相关性分析" | 交互式笔记本 | 计算相关性 → 生成热力图 |

---

## 三、标准工作流

### 3.1 前置条件

| 条件项 | 要求 | 检查方式 |
|--------|------|----------|
| 输入文件 | 与工作目录一致，命名无空格 | `ls -la` 确认 |
| 文件格式 | 支持 .csv/.xlsx/.json/.parquet | `file` 命令验证 |
| 数据规模 | 单文件 ≤ 2GB，行数 ≤ 500 万 | `wc -l` 预估 |
| 环境依赖 | Python 3.9+，已安装 pandas/plotly | `pip list` 检查 |
| URL 访问 | 目标站点允许匿名 GET 请求 | `curl -I` 测试 |

### 3.2 执行步骤（分步编号）

**Step 1：输入准备**
- 将待处理文件放入 `./input/` 目录
- 确认文件编码为 UTF-8（非 UTF-8 需先转换）
- 记录文件路径与预期输出格式

**Step 2：单样本试运行**
```bash
pretzelai --input ./input/sample.csv --output ./output/sample_report.md --mode explore
```
- 检查输出字段名、数据类型、图表是否正常
- 核对数值精度（保留 2 位小数）
- 确认 Markdown 表格渲染无异常

**Step 3：批量执行**
```bash
pretzelai --input ./input/ --output ./output/ --mode batch --format md
```
- 保留原始文件备份至 `./backup/`（`cp -r input backup/`）
- 每个文件独立生成报告，命名规则：`原文件名_report.md`
- 执行日志写入 `./logs/run_YYYYMMDD_HHMMSS.log`

**Step 4：结果校验**
- 抽查 3-5 个输出文件，核对关键字段与源数据一致性
- 验证图表标题、轴标签、图例无乱码
- 检查缺失值处理记录（报告中应包含缺失率统计）

### 3.3 输出规范

| 输出类型 | 格式 | 内容要求 |
|----------|------|----------|
| 探索报告 | Markdown | 数据概览、字段说明、缺失值统计、分布描述 |
| 可视化图表 | PNG (150dpi) | 标题、轴标签、图例、数据来源标注 |
| 结构化摘要 | JSON | `{"summary": {...}, "columns": [...], "charts": [...]}` |
| 批量报告 | 压缩包 ZIP | 包含所有报告 + 索引文件 `index.md` |

---

## 四、置信度门控

### 4.1 信息不足时的处理

当遇到以下情况，**不得编造数据**，必须输出占位符：

| 场景 | 占位符 | 示例 |
|------|--------|------|
| 字段含义不明确 | `[需核实:字段名]` | `[需核实:revenue_unit]` |
| 数据来源不可靠 | `[需核实:source_url]` | `[需核实:http://...]` |
| 统计方法不确定 | `[需核实:method]` | `[需核实:correlation_method]` |
| 时间范围缺失 | `[需核实:time_range]` | `[需核实:2023Q1-2023Q4]` |

### 4.2 置信度分级

| 级别 | 条件 | 输出策略 |
|------|------|----------|
| 高（≥90%） | 数据完整、来源明确、方法标准 | 正常输出结论 |
| 中（70-89%） | 部分字段缺失但可推断 | 输出结论 + 标注推断依据 |
| 低（<70%） | 数据严重缺失或矛盾 | 仅输出描述，不给出结论 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 文件不存在 | "未找到指定文件，请检查路径" | 1. 确认文件名 2. 检查目录权限 |
| E002 | 格式不支持 | "该文件格式不在支持列表内" | 1. 转换为 CSV 2. 检查扩展名 |
| E003 | 编码错误 | "文件编码非 UTF-8，解析失败" | 1. 用 `iconv` 转换 2. 指定编码参数 |
| E004 | 内存溢出 | "数据量超出内存限制" | 1. 分块读取 2. 采样分析 |
| E005 | URL 不可达 | "目标 URL 返回 403/404" | 1. 检查链接有效性 2. 添加 User-Agent |
| E006 | 列名冲突 | "存在重复列名，请重命名" | 1. 自动添加后缀 2. 手动指定映射 |
| E007 | 图表生成失败 | "绘图库未安装或版本不兼容" | 1. `pip install plotly` 2. 降级 matplotlib |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 忽略数据清洗 | 直接对含空值数据绘图 | 先执行缺失值处理，记录清洗日志 |
| 过度解读相关性 | 将相关性直接断言为因果 | 输出相关系数 + 显著性水平，注明"仅相关非因果" |
| 批量执行不校验 | 一次跑完所有文件不抽查 | 先单样本验证，再批量，最后抽检 10% |
| URL 抓取不设限 | 无超时和重试机制 | 设置 10s 超时，最多重试 3 次 |
| 输出格式混乱 | 不同文件输出不同结构 | 统一 JSON Schema，版本化控制 |

---

## 七、渐进式披露阅读路径

### 7.1 速查卡（30 秒上手）

```
1. 放文件 → 2. 跑单样本 → 3. 看报告 → 4. 批量跑 → 5. 抽检
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」确认需求匹配
2. 按「标准工作流」Step 1-2 执行单样本
3. 查看输出报告，理解字段含义
4. 遇到问题查「错误码体系」

### 7.3 进阶路径（熟练用户）

1. 自定义输出模板（修改 JSON Schema）
2. 集成到 CI/CD 流水线（定时批量执行）
3. 扩展数据源（添加自定义解析器）
4. 优化图表样式（传入 matplotlib 样式表）

---

## 八、参数参考表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | string | 必填 | 输入文件或目录路径 |
| `--output` | string | `./output/` | 输出目录 |
| `--mode` | enum | `explore` | `explore`/`batch`/`summary` |
| `--format` | enum | `md` | `md`/`json`/`png` |
| `--max-rows` | int | 100000 | 最大处理行数 |
| `--timeout` | int | 10 | URL 请求超时（秒） |
| `--retry` | int | 3 | 失败重试次数 |
| `--verbose` | bool | false | 输出详细日志 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用前请仔细阅读以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因使用本 Skill 产生的任何直接或间接损失，包括但不限于数据丢失、业务中断、决策失误等，Skill 作者及分发者不承担任何责任。

2. **数据安全**：使用者应确保输入数据不包含敏感个人信息或受法律保护的机密数据。因数据泄露或违规处理产生的法律后果由使用者自行承担。

3. **禁止反向工程**：未经明确书面许可，不得对本 Skill 的底层算法、提示词结构、决策逻辑进行反向工程、反编译或提取核心逻辑用于商业用途。

4. **合规使用**：使用者应遵守所在地法律法规，不得将本 Skill 用于任何非法目的，包括但不限于未经授权的数据抓取、隐私侵犯、欺诈行为等。

5. **免责声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权保证。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 LingData Studio

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

---

*本文档由 AI 辅助生成，仅供参考。使用前请结合具体场景验证功能适配性。*

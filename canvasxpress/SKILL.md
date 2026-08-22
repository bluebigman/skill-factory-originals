---
slug: canvasxpress
name: canvasxpress
displayName: 数据图表 交互可视化 审计追踪
description: 将数据文件转为可交互图表，并保留完整操作审计记录。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataVizForge
agent_created: true
trigger_words: ["数据可视化", "canvasxpress", "图表生成", "审计追踪", "数据分析", "交互图表", "可视化报表"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# CanvasXpress 交互图表生成与审计追踪 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 本 Skill 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 图表生成 | 将结构化数据文件转换为交互式 HTML 图表 | `canvasxpress --input sales.csv --chart-type bar` |
| 图表类型 | 支持柱状图、折线图、散点图、热力图等常见类型 | `--chart-type scatter` |
| 审计追踪 | 每次操作自动生成 `audit_log.json`，记录操作时间、参数、结果 | 查看 `audit_log.json` 即可追溯 |
| 错误报告 | 失败任务自动写入 `error_report.csv`，支持断点续跑 | 读取 CSV 后重新执行 |
| 自检功能 | 运行 `--selftest` 验证环境完整性 | `canvasxpress --selftest` |

### 1.2 本 Skill 不能做什么

| 限制项 | 说明 |
|--------|------|
| 数据清洗 | 不负责缺失值填充、异常值处理、格式转换等预处理工作 |
| 高级统计分析 | 不提供回归分析、假设检验、机器学习建模等统计功能 |
| 实时数据流 | 不支持流式数据接入，仅处理静态文件 |
| 图表样式深度定制 | 仅支持基础 CSS 修改，复杂动画/交互需手动编辑 HTML |
| 多语言输出 | 仅输出 HTML 格式，不生成 PDF、PNG 等静态图片 |

### 1.3 适用对象

- 需要快速将 CSV/Excel 数据转为可交互图表的分析师
- 需要保留操作记录以满足合规要求的团队
- 希望在不编写代码的情况下完成基础数据可视化的业务人员

---

## 二、触发方式

### 2.1 触发词

当对话中出现以下关键词时，本 Skill 将被激活：

- **直接触发**：数据可视化、canvasxpress、图表生成、审计追踪、数据分析
- **同义触发**：交互图表、可视化报表、图表制作、数据绘图

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 本 Skill 的响应 |
|------------------|----------|------------------|
| "帮我把这个 Excel 变成图表" | 将数据文件转为可视化图表 | 引导用户提供文件路径和图表类型，执行生成命令 |
| "我要能点来点去的图表" | 需要交互式图表而非静态图片 | 明确说明输出为 HTML 交互图表 |
| "做完图表我要知道谁在什么时候操作的" | 需要操作审计记录 | 展示 `audit_log.json` 的结构和查看方式 |
| "上次生成失败了，能接着来吗" | 需要错误恢复和断点续跑 | 读取 `error_report.csv`，定位失败原因并重新执行 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 验证方式 |
|------|------|----------|
| 数据文件 | CSV 或 Excel 格式，首行含列名 | 用 pandas 读取确认结构 |
| 数据质量 | 无严重缺失值、类型一致 | 运行 `df.info()` 检查 |
| 运行环境 | Python 3.8+，已安装 canvasxpress 包 | 运行 `canvasxpress --version` |
| 输出目录 | 有写权限的目录，用于存放 HTML 和日志 | `mkdir -p ./output` |

### 3.2 执行步骤

**Step 1：环境自检**

```bash
canvasxpress --selftest
```

预期输出：`All checks passed.` 或列出缺失依赖项。

**Step 2：生成图表**

```bash
canvasxpress --input data.csv --chart-type bar --output ./output/chart.html
```

参数说明：

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | 是 | 无 | 输入数据文件路径 |
| `--chart-type` | 是 | 无 | 图表类型：bar/line/scatter/heatmap |
| `--output` | 否 | `./chart.html` | 输出 HTML 文件路径 |
| `--title` | 否 | 文件名 | 图表标题 |
| `--width` | 否 | 800 | 图表宽度（像素） |
| `--height` | 否 | 600 | 图表高度（像素） |

**Step 3：查看结果**

- 用浏览器打开生成的 HTML 文件，确认图表渲染正确
- 检查数据点是否完整、坐标轴标签是否清晰

**Step 4：确认审计记录**

```bash
cat audit_log.json
```

预期看到类似结构：

```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "command": "canvasxpress --input data.csv --chart-type bar",
  "status": "success",
  "output_file": "./output/chart.html"
}
```

### 3.3 输出规范

| 输出物 | 格式 | 存放位置 |
|--------|------|----------|
| 交互图表 | HTML 文件 | 用户指定或默认当前目录 |
| 审计日志 | JSON 文件 | 与输出 HTML 同目录 |
| 错误报告 | CSV 文件 | 与输出 HTML 同目录 |

---

## 四、置信度门控

当输入信息不完整或存在歧义时，本 Skill 将使用占位符 `[需核实:字段]` 标记不确定内容，**绝不编造**。

| 场景 | 处理方式 | 示例 |
|------|----------|------|
| 缺少文件路径 | 输出 `[需核实:input_file_path]`，请用户补充 | "请提供数据文件路径，当前为 [需核实:input_file_path]" |
| 图表类型不明确 | 输出 `[需核实:chart_type]`，列出可选类型 | "图表类型未指定，可选：bar/line/scatter/heatmap，当前为 [需核实:chart_type]" |
| 数据列名不确定 | 输出 `[需核实:column_name]`，提示用户确认 | "数据中未找到 'date' 列，请确认列名，当前为 [需核实:column_name]" |
| 输出路径无权限 | 输出 `[需核实:output_path]`，建议更换目录 | "当前目录无写权限，请指定可写路径，当前为 [需核实:output_path]" |

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `E001` | 输入文件不存在 | "未找到输入文件，请检查路径是否正确" | 1. 确认文件路径；2. 检查文件名拼写；3. 重新执行 |
| `E002` | 图表类型不支持 | "不支持的图表类型，请从 bar/line/scatter/heatmap 中选择" | 1. 查看支持类型列表；2. 修改 `--chart-type` 参数；3. 重新执行 |
| `E003` | 数据格式错误 | "数据文件格式不正确，请确认首行为列名且数据完整" | 1. 用 pandas 读取检查；2. 清洗数据；3. 重新执行 |
| `E004` | 输出目录无权限 | "无法写入输出目录，请检查权限或更换路径" | 1. 更换输出目录；2. 修改目录权限；3. 重新执行 |
| `E005` | 依赖缺失 | "canvasxpress 未正确安装，请检查依赖" | 1. 运行 `pip install canvasxpress`；2. 运行 `--selftest`；3. 重新执行 |
| `E006` | 内存不足 | "处理数据时内存不足，请减小数据量或增加内存限制" | 1. 减少数据行数；2. 增加 `--memory-limit` 参数；3. 重新执行 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 反模式（错误做法） | 正确做法 | 说明 |
|---------------------|----------|------|
| 跳过数据清洗直接生成图表 | 先用 pandas 清洗数据 | 脏数据会导致图表失真或生成失败 |
| 忽略 `audit_log.json` | 定期查看审计日志 | 审计记录是合规审查和问题追溯的关键 |
| 失败后不查 `error_report.csv` 直接重跑 | 先分析错误原因再重试 | 盲目重跑可能重复同样的错误 |
| 用 Excel 打开 HTML 文件 | 用浏览器打开 | HTML 是网页格式，Excel 无法正确渲染 |
| 修改 HTML 后不保留原始文件 | 保留原始生成文件作为备份 | 修改出错时可回退到原始版本 |

### 6.2 反模式对照表

| 场景 | 反模式 | 推荐模式 |
|------|--------|----------|
| 数据量很大 | 一次性全部加载 | 分批处理或抽样预览 |
| 图表类型不确定 | 随意选一个 | 先查看数据分布再选类型 |
| 审计日志很大 | 不清理也不分析 | 定期归档并做趋势分析 |
| 多人协作 | 各自生成互不共享 | 统一输出目录和命名规范 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 1. 自检
canvasxpress --selftest

# 2. 生成柱状图
canvasxpress --input data.csv --chart-type bar

# 3. 查看结果
open chart.html

# 4. 确认审计
cat audit_log.json
```

### 7.2 分层次阅读路径

**新手路径（首次使用）**

1. 阅读「能力边界」了解能做什么、不能做什么
2. 按「标准流程」Step 1-2 完成一次试运行
3. 用浏览器打开输出 HTML 文件确认效果
4. 查看 `audit_log.json` 理解审计机制

**进阶路径（熟练用户）**

1. 自定义图表类型：修改 `--chart-type` 参数，尝试不同图表
2. 批量处理优化：调整并发数、内存限制参数
3. 审计日志分析：用 `audit_log.json` 做操作追溯和模式识别
4. 错误恢复：利用 `error_report.csv` 实现断点续跑

**专家路径（深度定制）**

1. 修改 HTML 中的 CSS 样式实现品牌定制
2. 编写脚本批量处理多个数据文件
3. 将审计日志接入企业监控系统

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。包括但不限于因数据错误、图表误读、操作失误等造成的任何直接或间接损失。

2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。

3. **合规使用**：使用者需确保使用本 Skill 的行为符合当地法律法规及所在组织的规定。

4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

5. **修改与分发**：允许修改和分发，但需保留原始版权声明。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2025 原创作者（自持版权）

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证功能。*

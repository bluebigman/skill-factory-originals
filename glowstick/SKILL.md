---
slug: glowstick
name: glowstick
displayName: 数据速绘 实时图表 可视化
description: 将文件或URL数据快速转为实时OpenGL图表，支持批量处理与校验。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinVisual
agent_created: true
trigger_words: ["glowstick", "实时绘图", "OpenGL图表", "数据可视化", "graphing", "快速成图", "数据速绘"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# glowstick — 数据速绘实时图表

本 Skill 由 AI 辅助生成，仅供参考。使用前请确认输入数据格式与目标环境兼容。

---

## 一、能力边界（一页纸速查卡）

### 能做什么
| 能力项 | 说明 |
|--------|------|
| 文件输入绘图 | 读取本地 CSV / JSON / TXT 等结构化数据文件，生成 OpenGL 实时图表 |
| URL 输入绘图 | 从 HTTP 地址拉取数据源，直接渲染为动态图表 |
| 批量处理 | 对同一目录下多个文件依次执行绘图，输出独立图表文件 |
| 字段校验 | 绘图前检查数据字段完整性，缺失时给出占位提示 |
| 试运行模式 | 用单条样本验证输出格式，再决定是否全量执行 |

### 不能做什么
| 限制项 | 说明 |
|--------|------|
| 不支持非结构化数据 | 如纯文本散文、扫描 PDF 等无法解析为数值序列的输入 |
| 不修改原始文件 | 所有操作只读源数据，输出图表文件另存 |
| 不保证实时性 | 图表为“实时渲染”指交互刷新，不涉及网络实时推送 |
| 不处理超大文件 | 单文件超过 200MB 时建议先拆分，否则可能内存溢出 |

### 适用对象
- 需要快速查看数据趋势的分析人员
- 需要批量生成图表用于汇报的团队
- 对 OpenGL 渲染有基础了解，希望用命令行工具简化流程的开发者

---

## 二、触发方式

### 触发词
`glowstick`、`实时绘图`、`OpenGL图表`、`数据可视化`、`graphing`、`快速成图`、`数据速绘`

### 场景映射表
| 你说的话（大白话） | 实际动作 |
|-------------------|----------|
| “帮我把这个 CSV 画成图” | 读取文件 → 识别数值列 → 生成 OpenGL 图表 |
| “这个 URL 里的数据能可视化吗” | 拉取 URL 内容 → 解析数据 → 渲染图表 |
| “我有 50 个文件要出图” | 批量模式：遍历目录 → 逐个绘图 → 汇总输出 |
| “先试一个看看效果” | 单样本试运行 → 输出预览 → 确认后再全量 |

---

## 三、标准流程

### 前置条件
1. 输入文件与当前工作目录一致，或提供完整路径。
2. 文件命名遵循 `数据名_日期.扩展名` 格式（如 `sales_20250101.csv`），便于批量识别。
3. 数据文件至少包含两列：一列作为 X 轴（时间或类别），一列作为 Y 轴（数值）。
4. 若使用 URL 输入，确保网络可访问且数据为 JSON 或 CSV 格式。

### 执行步骤
1. **准备输入**  
   将待处理文件放入同一目录，确认命名规范一致。  
   ```bash
   ls ./data/*.csv
   ```

2. **试运行**  
   用单个样本执行，核对输出字段与格式。  
   ```bash
   glowstick ./data/sales_20250101.csv --preview
   ```
   检查输出图表中的轴标签、数据点数量、颜色映射是否符合预期。

3. **批量执行**  
   确认无误后对全量数据执行，并保留原始文件备份。  
   ```bash
   cp -r ./data ./data_backup
   glowstick ./data/*.csv --output ./charts/
   ```

4. **校验结果**  
   抽查输出条目，核对关键字段与源数据一致。  
   ```bash
   glowstick --verify ./charts/sales_20250101.png --source ./data/sales_20250101.csv
   ```
   校验项包括：数据点总数、最大值/最小值、时间范围。

### 输出规范
| 输出项 | 格式 | 说明 |
|--------|------|------|
| 图表文件 | PNG / SVG | 默认 PNG，分辨率 1920×1080 |
| 元数据 | JSON | 包含源文件名、生成时间、数据统计摘要 |
| 日志 | stdout | 每步操作打印时间戳与状态码 |

---

## 四、置信度门控

当输入数据存在以下情况时，**不猜测、不编造**，直接输出占位符：

| 情况 | 输出 |
|------|------|
| 字段名无法识别 | `[需核实:字段名]` |
| 数值列缺失 | `[需核实:数值列]` |
| 时间格式不统一 | `[需核实:时间格式]` |
| URL 返回非预期内容 | `[需核实:数据源]` |

示例：
```
检测到文件 data_01.csv 缺少 Y 轴数值列，输出占位：
[需核实:数值列] → 请确认数据表头是否为 value / amount / count
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件不存在 | “未找到指定文件，请检查路径” | 确认路径或使用 `--dir` 指定目录 |
| `E002` | 数据格式不支持 | “仅支持 CSV / JSON / TXT 结构化数据” | 转换格式后重试 |
| `E003` | 字段缺失 | “缺少 X 轴或 Y 轴字段” | 检查表头，补充列名 |
| `E004` | URL 无法访问 | “网络请求失败，请检查地址或网络” | 换用本地文件或修复 URL |
| `E005` | 内存溢出 | “文件过大，建议拆分处理” | 使用 `--split` 参数或手动分割 |
| `E006` | 输出目录不可写 | “无法写入目标目录” | 修改权限或更换输出路径 |

---

## 六、FAQ 反模式

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 忽略试运行 | 直接批量执行，结果发现字段映射错误 | 先跑单样本，确认输出再全量 |
| 覆盖原始文件 | 批量输出到源目录，覆盖了 CSV | 输出到独立 `./charts/` 目录，保留备份 |
| 不校验结果 | 图表生成后不抽查，导致数据错位 | 用 `--verify` 抽查至少 3 个文件 |
| 依赖默认参数 | 不指定 X/Y 列，自动猜测失败 | 显式传入 `--x-column` 和 `--y-column` |
| 忽略日志 | 出错后无记录，难以回溯 | 保留 stdout 日志，或使用 `--log-file` 参数 |

---

## 七、渐进式披露

### 速查卡（30 秒上手）
```bash
# 单文件绘图
glowstick data.csv --x-column date --y-column value

# URL 绘图
glowstick https://api.example.com/data.json

# 批量绘图
glowstick ./data/*.csv --output ./charts/

# 校验
glowstick --verify ./charts/result.png --source data.csv
```

### 新手路径（第一次使用）
1. 准备一个两列 CSV 文件。
2. 运行 `glowstick yourfile.csv --preview` 查看预览。
3. 确认图表正常后，运行 `glowstick yourfile.csv --output result.png`。
4. 用 `--verify` 检查输出。

### 进阶路径（批量与自动化）
1. 统一文件命名，放入同一目录。
2. 使用通配符批量执行，输出到独立目录。
3. 编写脚本调用 `--verify` 自动校验所有输出。
4. 结合 cron 定时任务，实现数据更新后自动重绘。

---

## 八、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担全部责任。因使用本 Skill 导致的任何数据损失、业务中断或法律纠纷，均与 Skill 作者无关。
2. **禁止反向工程**：不得对本 Skill 的底层逻辑进行反向工程、反编译或试图提取源代码（除非适用法律允许）。
3. **合规使用**：使用者须确保输入数据来源合法，不包含侵犯第三方权益的内容。
4. **无担保**：本 Skill 按“现状”提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

本 Skill 采用 MIT 许可证发布。

```
MIT License

Copyright (c) 2025 LinVisual

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

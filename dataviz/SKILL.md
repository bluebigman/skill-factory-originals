---
slug: dataviz
name: dataviz
displayName: 演示报告 图表设计 数据呈现
description: 面向演示、报告与仪表盘场景的数据可视化设计指南与输出规范。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: VisualCraft Studio
agent_created: true
trigger_words: ["数据可视化", "图表设计", "可视化", "dashboard设计", "图表建议", "数据呈现", "图表选型", "可视化规范"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 数据可视化设计指南（dataviz Skill）

## 一、能力边界：一页纸速查卡

### 1.1 能做与不能做

| 维度 | ✅ 能做 | ❌ 不能做 |
|------|---------|-----------|
| 输入处理 | 读取 CSV、JSON、Excel（.xlsx）、Markdown 表格 | 不处理图片中的图表、不解析 PDF 内嵌数据 |
| 图表选型 | 根据数据维度、比较类型推荐图表类型 | 不生成最终图片文件（需借助其他工具渲染） |
| 设计规范 | 输出配色方案、字体层级、间距比例、标注规则 | 不提供品牌定制化设计（需人工介入） |
| 批量处理 | 对同目录下多文件执行统一规范检查 | 不自动修改源文件，仅输出建议报告 |
| 输出格式 | 生成 Markdown 报告、JSON 结构建议、字段映射表 | 不输出 HTML/CSS 代码片段 |

### 1.2 适用对象

- **演示场景**：PPT 页面中的单图设计、数据故事线编排
- **报告场景**：周报/月报中的趋势图、对比图、构成图
- **仪表盘场景**：多图表联动布局、KPI 卡片、筛选器交互

### 1.3 前置条件

| 条件项 | 要求 |
|--------|------|
| 文件命名 | 统一前缀（如 `data_2024_*.csv`），避免中文空格 |
| 数据字段 | 至少包含 1 个维度列 + 1 个度量列 |
| 数据质量 | 缺失值占比 < 20%，异常值需标注 |
| 目录结构 | 输入文件与输出报告分开放置（`/input` 与 `/output`） |

---

## 二、触发方式：场景映射表

| 用户说（大白话） | 触发词命中 | Skill 响应动作 |
|-----------------|-----------|---------------|
| "帮我看下这个数据怎么画图" | 数据可视化 | 分析字段类型，推荐 2-3 种图表方案 |
| "周报里的趋势图怎么设计好看" | 图表设计 | 输出配色、字体、标注规范建议 |
| "这个 dashboard 布局合理吗" | dashboard设计 | 检查信息层级、对比逻辑、视觉动线 |
| "我想比较 A 和 B 两组数据" | 图表建议 | 推荐对比型图表（分组柱状图、箱线图等） |
| "帮我检查一下这批图表的格式" | 可视化 | 批量执行规范检查，输出问题清单 |

---

## 三、标准流程：从输入到输出

### 3.1 执行步骤（分步编号）

**Step 1：环境确认（耗时约 1 分钟）**
- 检查当前目录下是否存在 `/input` 与 `/output` 文件夹，若无则创建
- 确认输入文件命名符合 `[前缀]_[日期]_[序号].[扩展名]` 格式
- 列出所有待处理文件清单，与用户确认范围

**Step 2：单样本试运行（耗时约 3 分钟）**
- 选取 1 个最小文件（或首行数据）执行完整流程
- 输出字段提取结果、图表类型推荐、设计规范建议
- 与用户核对输出格式是否符合预期

**Step 3：批量执行（耗时视数据量而定）**
- 对全量文件执行统一处理
- 每处理完一个文件，在 `/output` 下生成对应报告
- 原始文件不做任何修改，仅读取

**Step 4：结果校验（耗时约 2 分钟）**
- 抽查 3-5 个输出报告，核对关键字段（图表类型、配色方案、数据标签）与源数据一致
- 检查是否存在遗漏文件或重复处理
- 输出校验总结，标注通过率

### 3.2 输出规范

每个输入文件对应一份 Markdown 报告，结构如下：

```markdown
# 可视化建议报告：[文件名]

## 数据概况
- 行数：XXX | 列数：XXX
- 维度字段：[列表]
- 度量字段：[列表]

## 推荐图表方案
| 优先级 | 图表类型 | 适用理由 | 注意事项 |
|--------|---------|---------|---------|
| P0 | 折线图 | 时间趋势展示 | 数据点 < 20 时使用 |

## 设计规范建议
- 配色：主色 #2E86AB，辅色 #A23B72，强调色 #F18F01
- 字体：标题 18px 加粗，正文 14px 常规
- 间距：图表内边距 16px，图例距图表 12px

## 风险提示
- [需核实:字段名] 存在 15% 缺失值，建议补充或标注
```

---

## 四、置信度门控

### 4.1 信息不足时的处理

当遇到以下情况，**不得编造数据或结论**，必须输出占位符：

| 场景 | 输出内容 |
|------|---------|
| 字段含义不明确 | `[需核实:字段名_业务含义]` |
| 数据范围不确定 | `[需核实:数据时间范围]` |
| 图表类型无法确定 | `[需核实:比较维度]` |
| 配色方案无品牌参考 | `[需核实:品牌色板]` |

### 4.2 置信度分级

| 置信度 | 判定标准 | 输出策略 |
|--------|---------|---------|
| 高（≥90%） | 字段类型明确、数据量充足、场景清晰 | 直接输出推荐方案 |
| 中（70-89%） | 部分字段含义模糊 | 输出方案 + 标注需确认项 |
| 低（<70%） | 数据质量差或场景不明 | 仅输出数据概况，不推荐图表 |

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|---------|---------|---------|
| DV-001 | 输入文件为空 | "文件内容为空，请检查源数据" | 1. 确认文件未损坏 2. 检查编码格式 3. 重新导出 |
| DV-002 | 缺少度量列 | "未找到数值型字段，无法生成图表" | 1. 检查列类型 2. 确认数值列未被识别为文本 |
| DV-003 | 字段命名冲突 | "存在重复列名，请重命名后重试" | 1. 列出重复项 2. 添加后缀区分 |
| DV-004 | 数据量超出限制 | "单文件超过 10 万行，建议抽样处理" | 1. 随机抽样 10% 2. 或按时间维度聚合 |
| DV-005 | 输出目录不可写 | "无法写入输出文件，请检查权限" | 1. 确认目录存在 2. 修改写权限 3. 更换输出路径 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|---------|
| 图表堆砌 | 一个页面放 6+ 图表，无主次 | 每页聚焦 1 个核心结论，辅助图表折叠展示 |
| 配色混乱 | 使用 10+ 种颜色，无逻辑 | 主色 1 个 + 辅色 2 个 + 强调色 1 个，遵循 60-30-10 法则 |
| 忽略数据标注 | 图表无标题、无单位、无数据标签 | 每个图表必须包含：标题、坐标轴单位、关键数据点标注 |
| 类型误用 | 用饼图展示时间趋势 | 时间序列一律使用折线图或面积图 |
| 过度装饰 | 添加 3D 效果、阴影、渐变 | 保持扁平化设计，仅用颜色和大小区分层级 |

---

## 七、渐进式披露：分层次阅读路径

### 7.1 速查卡（30 秒上手）

```
1. 放文件 → 2. 跑单样本 → 3. 确认格式 → 4. 批量执行 → 5. 抽查校验
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」了解适用范围
2. 按「标准流程」Step 1-2 完成单样本测试
3. 对照「输出规范」确认报告格式
4. 遇到问题查「错误码体系」

### 7.3 进阶路径（熟练用户）

1. 直接进入批量执行阶段
2. 使用「置信度门控」快速定位需人工确认的字段
3. 参考「FAQ 反模式」优化图表设计质量
4. 自定义配色方案与字体规范，覆盖默认建议

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于数据解读偏差、图表误导风险、业务决策失误等。本 Skill 仅提供设计建议，不构成任何形式的数据分析结论或业务决策依据。

2. **禁止反向工程**：使用者不得对本 Skill 的提示词结构、生成逻辑、内部参数进行反向工程、破解、提取或二次分发。本 Skill 的创作思路与实现细节受版权保护。

3. **数据安全**：使用者需自行确保输入数据的合规性与安全性。本 Skill 不承担数据泄露、数据丢失或数据被未授权访问的责任。

4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 VisualCraft Studio

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证适用性。*

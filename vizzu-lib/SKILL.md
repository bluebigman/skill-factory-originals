---
slug: vizzu-lib
name: vizzu-lib
displayName: 数据叙事 动画图表 交互可视化
description: 将原始数据转化为可交互的动画图表，辅助构建数据故事。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Wei
agent_created: true
trigger_words: ["数据可视化", "动画图表", "数据故事", "动态图表", "图表库", "交互图表", "数据叙事"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# Vizzu-Lib Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 典型场景 |
|--------|------|----------|
| 数据转图表 | 将 CSV / JSON / 数组等原始数据映射为柱状图、折线图、散点图、面积图等基础图表 | 销售数据、用户增长、实验对比 |
| 动画过渡 | 在图表状态之间插入平滑动画，支持按维度拆分、聚合、排序变化 | 展示排名变化、时间序列演变 |
| 交互控制 | 通过点击、悬停、筛选器控制图表状态切换 | 仪表盘、演示文稿、数据报告 |
| 多图联动 | 同一数据源生成多个视图，通过事件同步联动 | 主图 + 明细表、全局 + 局部视图 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不做数据清洗 | 输入数据需已结构化，缺失值、异常值需提前处理 |
| 不做统计分析 | 不提供回归、显著性检验等统计计算，仅做可视化映射 |
| 不做复杂布局 | 不支持自由画布、自定义 SVG 图形、复杂仪表盘布局 |
| 不做导出服务 | 不生成图片/PDF 文件，仅提供浏览器内渲染 |

### 1.3 适用对象

- 需要快速将表格数据转为可演示图表的分析师、产品经理
- 需要制作数据故事（Data Story）的汇报人、教师
- 需要在网页中嵌入动态图表的开发者

---

## 二、触发方式

### 2.1 触发词

直接使用以下任一词汇即可激活本 Skill：

- 数据可视化
- 动画图表
- 数据故事
- 动态图表
- 图表库
- 交互图表
- 数据叙事

### 2.2 场景映射表

| 你说的话（大白话） | Skill 实际行为 |
|-------------------|----------------|
| "帮我把这几个月的销量做成动态图" | 读取数据 → 生成按时间轴动画的柱状图/折线图 |
| "我想展示各部门占比变化" | 生成堆叠柱状图或面积图，带过渡动画 |
| "做一个能点击切换指标的图表" | 生成多状态图表，绑定点击事件切换指标 |
| "把这份 CSV 变成图表" | 解析 CSV → 自动推断字段类型 → 生成默认图表 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| 数据格式 | CSV / JSON / 二维数组，首行或首对象为字段名 |
| 字段类型 | 至少一个维度字段（字符串/日期）+ 一个度量字段（数值） |
| 文件命名 | 建议使用 `data_*.csv` 或 `data_*.json` 模式，便于批量识别 |
| 环境 | 浏览器环境（Chrome / Firefox / Edge 最新版） |

### 3.2 执行步骤

#### 步骤 1：准备输入

1. 将待处理的数据文件放入当前工作目录。
2. 确认文件命名规范一致（例如 `sales_q1.csv`、`sales_q2.csv`）。
3. 检查数据文件编码为 UTF-8，避免中文乱码。

#### 步骤 3：试运行

1. 选取单个样本文件（如 `sales_q1.csv`）执行可视化。
2. 核对输出图表的字段映射是否正确：
   - 维度字段是否被正确识别为横轴/分组；
   - 度量字段是否被正确识别为纵轴/数值。
3. 检查动画过渡是否流畅，无卡顿或跳变。

#### 步骤 4：批量执行

1. 确认样本无误后，对全量数据文件执行。
2. 保留原始文件备份（建议复制到 `backup/` 目录）。
3. 每个文件独立生成一个图表实例，不互相覆盖。

#### 步骤 5：校验结果

1. 抽查 3-5 个输出图表。
2. 核对关键字段（如时间、数值）与源数据是否一致。
3. 确认交互功能（点击、悬停）正常响应。

### 3.3 输出规范

| 输出项 | 规范 |
|--------|------|
| 图表类型 | 默认柱状图；若数据含时间字段则自动切换为折线图 |
| 颜色方案 | 默认使用 `#4C78A8` 系配色，可自定义 |
| 动画时长 | 默认 800ms，可配置范围 200ms - 2000ms |
| 交互事件 | 支持 `click`、`hover`、`legend` 切换 |

---

## 四、置信度门控

当输入数据存在以下情况时，本 Skill 不会猜测或编造，而是输出占位符 `[需核实:字段名]`：

| 情况 | 输出行为 |
|------|----------|
| 字段名缺失或为空 | 输出 `[需核实:字段名]`，不自动命名 |
| 数值字段含非数字字符 | 输出 `[需核实:数值字段]`，不强制转换 |
| 时间字段格式不统一 | 输出 `[需核实:时间格式]`，不自动解析 |
| 数据量超过 10,000 条 | 输出 `[需核实:数据量]`，提示需抽样或聚合 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 数据文件不存在 | "未找到指定数据文件，请检查路径" | 确认文件路径与命名 |
| `E002` | 字段类型无法识别 | "无法识别维度/度量字段，请检查数据格式" | 确保首行为字段名，数值列为纯数字 |
| `E003` | 动画渲染失败 | "动画渲染失败，请检查浏览器兼容性" | 升级浏览器或切换至 Chrome |
| `E004` | 数据量超限 | "数据量过大，建议抽样或聚合" | 对数据进行降采样 |
| `E005` | 交互事件未绑定 | "交互事件未生效，请检查配置" | 确认事件绑定代码正确 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式（错误做法） | 正确做法 |
|----|-------------------|----------|
| 数据格式混乱 | 直接传入含合并单元格的 Excel 导出文件 | 先转为标准 CSV，确保每行一条记录 |
| 字段名含空格 | 不处理直接使用 | 统一替换为下划线，如 `sales_amount` |
| 时间字段为字符串 | 直接作为维度使用 | 先转换为 Date 类型，再映射到时间轴 |
| 动画过度使用 | 所有图表都加动画 | 仅对需要强调变化的数据使用动画 |
| 忽略交互 | 只生成静态图 | 至少绑定一个点击事件，提升可探索性 |

### 6.2 反模式对照

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 一次性渲染 100 个图表 | 页面卡顿 | 分批渲染，或使用虚拟滚动 |
| 使用 10 种以上颜色 | 视觉混乱 | 限制在 5 种以内，使用色盲友好配色 |
| 动画时长设为 5 秒 | 用户等待过长 | 控制在 1 秒以内 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 放数据文件到当前目录
2. 调用触发词（如"数据可视化"）
3. 等待自动生成图表
4. 点击图表查看交互效果
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」了解适用范围。
2. 准备一个简单的 CSV 文件（2 列：维度 + 数值）。
3. 执行「标准流程」的步骤 1-3。
4. 查看输出图表，熟悉交互操作。

### 7.3 进阶路径（熟练用户）

1. 掌握「错误码体系」，快速定位问题。
2. 自定义颜色、动画时长、图表类型。
3. 使用多图联动，构建数据故事。
4. 结合「置信度门控」，处理复杂数据场景。

---

## 八、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担全部责任。因使用本 Skill 产生的任何直接或间接损失，Skill 作者及 AI 辅助生成方不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 的底层逻辑、提示词结构进行反向工程、破解或二次分发用于商业用途。
3. **合规使用**：使用者需确保输入数据不违反法律法规，不包含敏感个人信息。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

本 Skill 采用 MIT 许可证发布。

```
MIT License

Copyright (c) 2024 Lin Wei

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*

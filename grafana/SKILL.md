---
slug: grafana
name: grafana
displayName: 数据可视化 观测分析 图表构建
description: 将多源数据转化为可视化图表与观测分析结果，辅助决策。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 观澜工坊
agent_created: true
trigger_words: ["grafana", "数据可视化", "观测分析", "图表构建", "dashboard", "可视化看板", "指标监控"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# Grafana 数据可视化与观测分析 Skill

## 一、能力边界速查卡

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| 数据接入 | 支持 CSV、JSON、Parquet 等结构化文件；支持常见数据库查询结果导入 | 不处理非结构化文本、图片、音视频数据 |
| 图表构建 | 生成折线图、柱状图、饼图、热力图、仪表盘等 20+ 种可视化类型 | 不生成 3D 交互模型或自定义渲染引擎 |
| 观测分析 | 提供趋势分析、异常点标注、阈值告警规则建议 | 不做预测性建模或机器学习推断 |
| 仪表盘编排 | 支持多面板布局、时间范围筛选、变量模板配置 | 不替代 Grafana 服务端部署与运维 |
| 数据校验 | 检查字段完整性、类型一致性、时间戳格式 | 不自动修复源数据错误 |

### 1.2 适用对象

- **数据分析师**：快速将业务数据转化为可视化看板
- **运维工程师**：构建系统指标监控面板
- **产品经理**：制作数据汇报图表
- **数据工程师**：验证数据管道输出质量

### 1.3 输入输出规范

| 项目 | 要求 |
|------|------|
| 输入格式 | CSV（UTF-8 编码）、JSON（数组或对象）、Parquet |
| 文件命名 | `数据源名称_日期.csv`，如 `订单数据_20250101.csv` |
| 输出格式 | 图表 JSON 配置 + 观测分析报告（Markdown） |
| 输出目录 | 与输入文件同目录下的 `output/` 文件夹 |

---

## 二、触发方式与场景映射

### 2.1 触发词

- 主触发词：`grafana`、`数据可视化`、`观测分析`、`图表构建`、`dashboard`
- 补充触发词：`可视化看板`、`指标监控`、`数据图表`

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 本 Skill 响应 |
|------------------|----------|---------------|
| "帮我把这个月的销售数据画成图" | 生成销售趋势图表 | 读取 CSV → 识别时间字段 → 生成折线图配置 |
| "看看服务器 CPU 使用率有没有异常" | 监控指标异常检测 | 分析时间序列 → 标注超出阈值的数据点 |
| "做一个大屏展示所有业务指标" | 构建综合仪表盘 | 多面板布局 + 变量模板配置 |
| "这些数据怎么画比较合适" | 图表类型推荐 | 根据字段类型和分布推荐 2-3 种图表方案 |

---

## 三、标准执行流程

### 3.1 前置条件

1. 确认输入文件已放入当前工作目录
2. 检查文件编码为 UTF-8（非 UTF-8 需先转换）
3. 确认文件命名符合 `数据源名称_日期.csv` 规范
4. 若为多文件批量处理，确认所有文件命名前缀一致

### 3.2 执行步骤

#### 步骤 1：数据探查（30 秒）

```bash
# 查看文件前 5 行，确认字段结构
head -5 订单数据_20250101.csv

# 统计行数与字段数
wc -l 订单数据_20250101.csv
```

**核对要点**：
- 字段名是否清晰（如 `timestamp`、`value`、`region`）
- 时间字段格式是否统一（`YYYY-MM-DD HH:mm:ss` 或 `YYYY-MM-DD`）
- 数值字段是否包含非数字字符

#### 步骤 2：单样本试运行

选取 1 个文件执行完整流程：

```bash
# 生成图表配置
grafana 数据可视化 --input 订单数据_20250101.csv --chart-type line --time-field timestamp --value-field amount

# 生成观测分析报告
grafana 观测分析 --input 订单数据_20250101.csv --time-field timestamp --value-field amount --threshold 10000
```

**输出核对**：
- 图表 JSON 中 `targets[0].refId` 是否正确引用数据源
- 分析报告中时间范围是否覆盖完整数据
- 阈值告警规则是否合理（不出现 0 条或全部命中的极端情况）

#### 步骤 3：批量执行

```bash
# 对目录下所有匹配文件执行
for f in 订单数据_*.csv; do
  grafana 数据可视化 --input "$f" --chart-type line --time-field timestamp --value-field amount
  grafana 观测分析 --input "$f" --time-field timestamp --value-field amount --threshold 10000
done
```

**执行前备份**：

```bash
mkdir -p backup_$(date +%Y%m%d)
cp *.csv backup_$(date +%Y%m%d)/
```

#### 步骤 4：结果校验

| 校验项 | 方法 | 通过标准 |
|--------|------|----------|
| 数据完整性 | 对比源文件行数与图表数据点数 | 差异 ≤ 1%（排除空值行） |
| 字段映射 | 抽查 3 个时间点，核对图表数值与源数据一致 | 100% 匹配 |
| 时间范围 | 检查图表 x 轴起止时间 | 与源数据 min/max 一致 |
| 告警规则 | 检查阈值设置 | 告警数量在数据总量的 1%-20% 之间 |

### 3.3 输出规范

**图表配置 JSON 结构**：

```json
{
  "dashboard": {
    "title": "订单数据_20250101",
    "panels": [
      {
        "type": "timeseries",
        "title": "订单金额趋势",
        "targets": [
          {
            "refId": "A",
            "query": "SELECT timestamp, amount FROM orders WHERE date = '2025-01-01'"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "currency",
            "thresholds": {
              "steps": [
                {"color": "green", "value": null},
                {"color": "red", "value": 10000}
              ]
            }
          }
        }
      }
    ]
  }
}
```

**观测分析报告结构**：

```markdown
# 观测分析报告：订单数据_20250101

## 数据概览
- 总记录数：1,234 条
- 时间范围：2025-01-01 00:00 ~ 2025-01-01 23:59
- 缺失值：12 条（0.97%）

## 趋势分析
- 整体趋势：上升（+15.3% 环比）
- 峰值时间：14:30（金额 15,200 元）
- 谷值时间：03:15（金额 1,800 元）

## 异常检测
- 超出阈值（10,000 元）记录：23 条（1.86%）
- 异常时间段：09:00-10:00、14:00-15:00

## 建议
- 关注 09:00-10:00 时段订单激增原因
- 考虑对 14:00-15:00 时段增加库存预警
```

---

## 四、置信度门控

### 4.1 信息不足处理

当遇到以下情况时，输出 `[需核实:字段]` 占位符，不编造数据：

| 场景 | 处理方式 |
|------|----------|
| 时间字段缺失 | `[需核实:timestamp字段]` 并提示用户指定时间列 |
| 数值字段含非数字字符 | `[需核实:value字段格式]` 并列出异常值示例 |
| 阈值未指定 | `[需核实:threshold阈值]` 并建议使用均值±2σ |
| 文件编码无法识别 | `[需核实:文件编码]` 并提示使用 `file` 命令检测 |

### 4.2 置信度分级

| 置信度 | 条件 | 输出行为 |
|--------|------|----------|
| 高（≥90%） | 字段完整、格式规范、无缺失 | 直接输出完整结果 |
| 中（70%-89%） | 少量缺失值或格式不一致 | 输出结果 + 标注需人工复核的点 |
| 低（<70%） | 关键字段缺失或大量异常 | 仅输出数据探查报告，不生成图表 |

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 文件不存在 | "未找到输入文件，请检查路径" | 1. 确认文件在当前目录；2. 检查文件名拼写 |
| E002 | 文件格式不支持 | "仅支持 CSV、JSON、Parquet 格式" | 1. 转换文件格式；2. 确认扩展名正确 |
| E003 | 时间字段缺失 | "未找到时间字段，请指定 --time-field" | 1. 查看文件头确认字段名；2. 重新指定参数 |
| E004 | 数值字段含非数字 | "数值字段包含非数字字符" | 1. 定位异常行；2. 清洗数据后重试 |
| E005 | 阈值设置不合理 | "阈值导致 0 条或全部记录命中" | 1. 检查阈值范围；2. 使用分位数建议值 |
| E006 | 输出目录无权限 | "无法写入输出目录" | 1. 检查目录权限；2. 指定其他输出路径 |
| E007 | 批量执行中断 | "批量处理在第 N 个文件中断" | 1. 查看错误日志；2. 从失败文件继续执行 |

---

## 六、FAQ 反模式对照

### 6.1 常见坑与反模式

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|---------------------|----------|
| 忽略数据清洗 | 直接对含缺失值的数据生成图表 | 先执行缺失值统计，标注或填充后再可视化 |
| 图表类型误选 | 用饼图展示 50+ 类别的分布 | 改用条形图或热力图 |
| 时间格式混乱 | 混用 `2025/01/01` 和 `2025-01-01` | 统一转换为 ISO 8601 格式 |
| 阈值拍脑袋 | 随意设定固定阈值 | 使用分位数（P95/P99）或均值±3σ |
| 忽略数据源标注 | 图表无数据来源说明 | 在图表标题或注释中标注数据源与生成时间 |

### 6.2 反模式自查清单

- [ ] 是否在图表中标注了数据源？
- [ ] 是否对缺失值进行了说明？
- [ ] 阈值设定是否有统计依据？
- [ ] 时间字段格式是否统一？
- [ ] 是否保留了原始文件备份？

---

## 七、渐进式披露路径

### 7.1 速查卡（30 秒上手）

```
1. 放文件 → 2. 跑单样本 → 3. 核对输出 → 4. 批量执行 → 5. 校验结果
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界速查卡」了解适用范围
2. 按「标准执行流程」步骤 1-2 完成单样本试运行
3. 核对输出是否符合预期
4. 参考「FAQ 反模式对照」避免常见错误

### 7.3 进阶路径（熟练用户）

1. 深入理解「置信度门控」机制，处理复杂数据场景
2. 使用「错误码体系」快速定位和解决问题
3. 自定义阈值规则与告警策略
4. 结合多数据源构建综合仪表盘

---

## 八、参数速查表

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--input` | string | 是 | 无 | 输入文件路径 |
| `--chart-type` | string | 否 | line | 图表类型（line/bar/pie/heatmap） |
| `--time-field` | string | 是 | 无 | 时间字段名 |
| `--value-field` | string | 是 | 无 | 数值字段名 |
| `--threshold` | float | 否 | 无 | 告警阈值 |
| `--output-dir` | string | 否 | ./output | 输出目录 |
| `--selftest` | flag | 否 | false | 运行自检 |
| `--version` | flag | 否 | false | 显示版本 |

---

## 用户协议

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的所有输出仅供参考，不构成任何形式的专业建议或决策依据。
2. **禁止反向工程**：使用者不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码、核心算法。
3. **合规使用**：使用者应确保使用本 Skill 处理的数据符合相关法律法规，不得用于任何非法用途。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

<!-- user-agreement-injected -->

---

## 许可证（License）

### MIT License

```
MIT License

Copyright (c) 2025 观澜工坊

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

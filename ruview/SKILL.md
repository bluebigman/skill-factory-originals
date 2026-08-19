---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ruview
name: ruview
displayName: 无线感知 空间监测 信号分析
description: 将WiFi信号转化为空间感知与存在检测的结构化分析结果。
version: 1.0.3
rules_version: cpr-20260819-n551
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ruview
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SignalForge Lab
agent_created: true
trigger_words: ["ruview", "WiFi感知", "无线信号分析", "空间监测", "存在检测", "信号测绘", "室内定位"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# ruview — 无线感知与空间存在检测分析 Skill

## 1. 能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入要求 | 输出产物 |
|--------|------|----------|----------|
| 信号强度解析 | 从 WiFi 扫描记录中提取 RSSI、信道、BSSID 等基础特征 | CSV / JSON / PCAP 解析后的结构化文件 | 标准化特征表 |
| 空间状态推断 | 基于信号波动模式判断空间内是否有人活动 | 连续时间序列信号数据（≥30 秒） | 存在/空闲/不确定 三态标签 |
| 区域变化检测 | 识别信号指纹的漂移与突变，标记环境变化事件 | 同一空间多时段采样数据 | 事件时间线 |
| 批量报告生成 | 对多文件批量执行分析并汇总统计 | 目录内命名规范一致的多个文件 | 汇总报告 + 逐条明细 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不做人员身份识别 | 无法区分具体个体，仅能判断"有/无活动" |
| 不做实时监控 | 本 Skill 为离线分析工具，不接入实时数据流 |
| 不做穿墙精确定位 | 仅基于信号强度变化做粗粒度空间状态判断，不输出坐标 |
| 不做隐私数据采集 | 不获取设备 MAC 地址之外的任何个人信息，且 MAC 仅作特征使用 |

### 1.3 适用对象

- 需要做空间占用率统计的办公场所管理者
- 研究无线信号与人类活动关联性的技术人员
- 需要低成本存在检测方案的 IoT 爱好者
- 对室内空间动态变化感兴趣的数据分析人员

---

## 2. 触发方式

### 2.1 触发词

当你的输入中包含以下任一关键词时，本 Skill 自动激活：

- `ruview`
- `WiFi感知`
- `无线信号分析`
- `空间监测`
- `存在检测`
- `信号测绘`
- `室内定位`

### 2.2 场景映射表

| 用户说（大白话） | Skill 实际执行动作 |
|------------------|-------------------|
| "帮我看看这个办公室下午有没有人待过" | 解析信号时间序列 → 输出存在/空闲标签 |
| "这几个 WiFi 数据文件帮我一起分析下" | 批量执行 → 生成汇总报告 |
| "这个信号数据怎么感觉怪怪的" | 执行变化检测 → 标记异常时间点 |
| "ruview 怎么用？" | 输出本 Skill 的快速上手指南 |

---

## 3. 标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方法 |
|------|------|----------|
| 文件格式 | CSV（逗号分隔）或 JSON（数组格式） | 用文本编辑器打开确认 |
| 必填字段 | `timestamp`（ISO8601）、`rssi`（整数 dBm）、`bssid`（MAC 地址） | 查看文件头 |
| 时间跨度 | 单文件连续记录 ≥ 30 秒 | 统计首尾时间戳差值 |
| 命名规范 | `{空间名}_{日期}_{批次}.csv`，如 `officeA_20260819_01.csv` | 目视检查 |

### 3.2 执行步骤

#### 第一步：准备输入

1. 将待处理文件放入同一工作目录。
2. 确认所有文件命名符合 `{空间名}_{日期}_{批次}.csv` 规范。
3. 如命名不一致，先重命名再继续。

#### 第二步：试运行单样本

1. 选取一个文件执行单样本分析：
   ```
   ruview analyze --input officeA_20260819_01.csv
   ```
2. 核对输出字段是否包含：`timestamp`、`bssid`、`rssi`、`state`（存在/空闲/不确定）。
3. 检查 `state` 字段取值是否在预期范围内。

#### 第三步：批量执行

1. 确认单样本无误后，对全量数据执行：
   ```
   ruview batch --input-dir ./data --output-dir ./results
   ```
2. 执行前自动备份原始文件至 `./backup_原始时间戳/` 目录。
3. 批量执行期间不修改任何源文件。

#### 第四步：校验结果

1. 随机抽取 5% 输出条目，人工核对 `timestamp` 与源数据是否一致。
2. 检查 `state` 为"存在"的条目，其对应时间段的 RSSI 方差是否 > 3 dBm（合理波动范围）。
3. 如发现异常，回退至第二步重新调整参数。

### 3.3 输出规范

| 输出项 | 格式 | 示例 |
|--------|------|------|
| 单文件分析结果 | JSON 对象 | `{"file":"officeA_20260819_01.csv","total_records":1200,"state":"存在","confidence":0.87}` |
| 批量汇总报告 | Markdown 表格 | 见下方示例 |
| 事件时间线 | CSV 文件 | `event_start,event_end,event_type,confidence` |

批量汇总报告示例：

| 文件 | 记录数 | 判定状态 | 置信度 | 备注 |
|------|--------|----------|--------|------|
| officeA_20260819_01.csv | 1200 | 存在 | 0.87 | 14:02-14:35 有持续活动 |
| officeA_20260819_02.csv | 800 | 空闲 | 0.92 | 全天无显著波动 |
| officeB_20260819_01.csv | 1500 | 不确定 | 0.55 | 信号源不稳定，建议重采 |

---

## 4. 置信度门控

### 4.1 判定规则

| 条件 | 输出状态 | 置信度范围 |
|------|----------|------------|
| RSSI 标准差 > 3 dBm 且持续 > 30 秒 | 存在 | 0.7 - 0.95 |
| RSSI 标准差 < 1 dBm 且持续 > 5 分钟 | 空闲 | 0.8 - 0.95 |
| 数据量 < 30 条 或 时间跨度 < 30 秒 | 不确定 | 0.3 - 0.5 |
| 信号源数量 < 3 个 | 不确定 | 0.4 - 0.6 |

### 4.2 信息不足时的处理

当输入数据不满足前置条件时，输出中必须包含 `[需核实:字段名]` 占位符，禁止编造数值。

示例：
```json
{
  "file": "unknown_20260819.csv",
  "state": "不确定",
  "confidence": 0.4,
  "missing_fields": ["timestamp", "bssid"],
  "note": "[需核实:timestamp格式] [需核实:bssid字段存在性]"
}
```

---

## 5. 错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E1001` | 文件不存在 | "未找到指定文件，请检查路径" | 1. 确认文件路径正确 2. 检查文件名大小写 |
| `E1002` | 字段缺失 | "缺少必填字段，请检查文件头" | 1. 查看文件头 2. 补充缺失字段 3. 重新执行 |
| `E1003` | 时间格式错误 | "时间戳格式不符合 ISO8601" | 1. 转换时间格式 2. 重新执行 |
| `E2001` | 数据量不足 | "有效数据不足 30 条，无法判定" | 1. 延长采集时间 2. 合并多个批次 |
| `E2002` | 信号源过少 | "检测到少于 3 个 BSSID，结果不可靠" | 1. 增加采集点 2. 重新采集 |
| `E3001` | 批量执行中断 | "批量执行在第 N 个文件处中断" | 1. 查看错误日志 2. 修复对应文件 3. 从断点续跑 |

---

## 6. FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式表现 | 正确做法 |
|----|------------|----------|
| 忽略时间同步 | 不同设备采集的时间戳基准不一致，导致状态误判 | 采集前统一设备时间，或使用 NTP 同步 |
| 信号源漂移 | 路由器重启后 BSSID 变化，被误判为环境突变 | 分析前先做 BSSID 映射归一化 |
| 过度依赖单一指标 | 仅看 RSSI 均值，忽略方差变化 | 同时关注均值、方差、变化频率三个维度 |
| 小样本强行判定 | 10 秒数据就下"存在"结论 | 严格遵循置信度门控，不足则输出"不确定" |
| 忽略环境基线 | 没有采集空房间基线数据 | 先采集 10 分钟空房间数据作为对照 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| "这个数据肯定有人" | 无依据的绝对化判断 | 输出置信度，让用户自行决策 |
| "把所有文件都跑一遍" | 未做单样本验证就批量执行 | 先试运行 1 个文件，确认无误再批量 |
| "结果不对就调参数" | 盲目调参导致过拟合 | 先检查数据质量，再考虑参数调整 |

---

## 7. 渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 放文件 → 命名规范：{空间}_{日期}_{批次}.csv
2. 试运行 → ruview analyze --input 文件.csv
3. 看结果 → 检查 state 字段
4. 批量跑 → ruview batch --input-dir ./data --output-dir ./results
5. 校验 → 抽查 5% 条目，核对时间戳
```

### 7.2 新手路径（首次使用）

1. 阅读第 1 节，了解能力边界。
2. 按第 3.1 节检查数据格式。
3. 执行第 3.2 节第二步的试运行命令。
4. 对照第 4 节理解输出置信度含义。
5. 遇到问题查第 5 节错误码表。

### 7.3 进阶路径（熟练用户）

1. 深入理解第 4 节置信度门控的判定逻辑。
2. 根据第 6 节反模式优化采集方案。
3. 自定义分析参数（如调整方差阈值）。
4. 结合事件时间线输出做空间使用率统计。

---

## 8. 参数参考表

| 参数名 | 默认值 | 允许范围 | 说明 |
|--------|--------|----------|------|
| `--variance-threshold` | 3.0 | 1.0 - 10.0 | RSSI 标准差阈值，低于此值视为稳定 |
| `--min-duration` | 30 | 10 - 300 | 判定"存在"所需的最短持续秒数 |
| `--min-bssid-count` | 3 | 1 - 10 | 有效信号源最小数量 |
| `--confidence-floor` | 0.5 | 0.1 - 0.9 | 低于此置信度输出"不确定" |
| `--batch-size` | 100 | 10 - 1000 | 批量执行时每批处理文件数 |

---

## 9. 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的分析结果仅供参考，不构成任何形式的专业建议或决策依据。
2. **禁止反向工程**：不得对本 Skill 的底层算法、提示词结构、生成逻辑进行反向工程、破解、篡改或二次分发。
3. **数据合规**：使用者须确保输入数据符合当地法律法规，不得使用本 Skill 处理涉及个人隐私的敏感数据。
4. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性担保。

<!-- user-agreement-injected -->

---

## 10. 许可证（License）

本 Skill 采用 MIT 许可证授权：

```
MIT License

Copyright (c) 2026 原创作者（自持版权）

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

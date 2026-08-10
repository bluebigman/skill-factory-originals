---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: data-backup-checklist
name: data-backup-checklist
displayName: 备份核对 差异追踪 恢复演练
description: 备份清单核对、版本差异追踪、恢复演练评分与风险分级预警。
version: 2.0.1
rules_version: cpr-20260810-n301
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/data-backup-checklist
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨研
agent_created: true
trigger_words: ["data-backup-checklist", "备份检查", "备份核对", "备份完整性", "恢复演练", "版本差异"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 备份核对与恢复演练 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输出物 |
|--------|------|--------|
| 备份清单核对 | 对备份任务清单逐项检查，确认备份策略、保留周期、存储位置等配置项是否齐全 | 核对结果表（含缺失项标注） |
| 版本差异追踪 | 对比同一数据集的两次备份版本，列出新增、删除、修改的文件/记录 | 差异清单（含变更类型与时间戳） |
| 恢复演练评分 | 对恢复演练过程按预设评分卡打分，评估恢复时效、数据完整性、操作规范性 | 评分报告（含分项得分与总评） |
| 风险分级预警 | 根据核对与演练结果，按严重程度输出风险等级（低/中/高/严重） | 预警通知（含风险描述与建议动作） |

### 1.2 不能做什么

- 不能直接执行备份或恢复操作（本 Skill 仅提供核对、追踪、评分与预警的分析框架）
- 不能替代专业备份软件（如 Veeam、Commvault）的底层调度与存储管理
- 不能自动修复备份失败或数据损坏问题（仅能定位问题并给出排查方向）
- 不能对未提供元数据或日志的数据集进行深度分析（需依赖输入数据的完整度）

### 1.3 适用对象

- 运维工程师：日常备份任务巡检与异常排查
- 数据管理员：备份策略合规性审查与版本管理
- 灾备演练负责人：恢复演练的组织、评分与复盘
- 审计人员：备份与恢复流程的合规性验证

---

## 二、触发方式

### 2.1 触发词

| 触发词 | 场景示例 |
|--------|----------|
| `data-backup-checklist` | 直接调用 Skill 主命令 |
| `备份检查` | "帮我做一次数据库的备份检查" |
| `备份核对` | "核对一下上周的备份清单是否完整" |
| `备份完整性` | "验证备份文件是否齐全、有无缺失" |
| `恢复演练` | "组织一次恢复演练，并给出评分" |
| `版本差异` | "对比昨天和今天的备份版本差异" |

### 2.2 场景映射表

| 用户说（大白话） | Skill 实际执行 |
|------------------|----------------|
| "看看备份有没有漏" | 执行备份清单核对，输出缺失项 |
| "这两个备份有啥不一样" | 执行版本差异追踪，输出变更清单 |
| "演练结果咋样" | 执行恢复演练评分，输出评分报告 |
| "备份风险高不高" | 执行风险分级预警，输出风险等级与建议 |
| "帮我检查一下备份环境" | 执行环境预检（Python 版本、依赖库） |

---

## 三、标准流程

### 3.1 前置条件

| 条件项 | 要求 | 验证方式 |
|--------|------|----------|
| Python 版本 | 3.9 及以上 | 执行 `python --version` |
| openpyxl 库 | 已安装（如需 Excel 支持） | 执行 `pip show openpyxl` |
| 输入数据 | 备份清单（CSV/JSON/Excel）、备份日志、恢复演练记录 | 确认文件路径可读且格式正确 |

### 3.2 执行步骤

#### 步骤 1：环境预检

```bash
data-backup-checklist --selftest
```

- 检查 Python 版本是否为 3.9+
- 确认 `openpyxl` 是否已安装
- 查看 stderr 输出中的具体失败断言

**输出示例：**

```
[OK] Python 3.10.12
[OK] openpyxl 3.1.2
[PASS] 环境预检通过
```

#### 步骤 2：加载备份清单

- 支持格式：CSV、JSON、Excel（.xlsx）
- 必填字段：`backup_id`、`backup_time`、`source_path`、`target_path`、`status`、`retention_days`
- 可选字段：`checksum`、`size_bytes`、`backup_type`（全量/增量/差异）

**参数表：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `--input` | string | 是 | 备份清单文件路径 |
| `--format` | string | 否 | 输入格式（默认自动检测） |
| `--output` | string | 否 | 输出报告路径（默认 stdout） |

#### 步骤 3：执行核对与追踪

- 核对项：备份任务是否覆盖所有关键数据源、保留周期是否合规、状态是否为 `success`
- 差异追踪：对比两个时间点的备份版本，输出变更明细

**核对规则：**

| 检查项 | 通过条件 | 失败提示 |
|--------|----------|----------|
| 覆盖率 | 所有关键数据源均有备份任务 | `[需核实:未覆盖的数据源]` |
| 保留周期 | `retention_days >= 30` | `[需核实:保留周期不足]` |
| 状态 | `status == "success"` | `[需核实:备份失败]` |

#### 步骤 4：恢复演练评分

**评分卡（总分 100 分）：**

| 评分维度 | 分值 | 评分标准 |
|----------|------|----------|
| 恢复时效 | 30 分 | RTO 达标（≤4 小时）得满分，每超 1 小时扣 5 分 |
| 数据完整性 | 40 分 | 数据校验通过率 100% 得满分，每降 1% 扣 2 分 |
| 操作规范性 | 30 分 | 演练流程符合预案得满分，每偏离一项扣 5 分 |

**输出规范：**

```
恢复演练评分报告
================
恢复时效: 28/30 (RTO 实际 4.5 小时)
数据完整性: 38/40 (校验通过率 99.5%)
操作规范性: 25/30 (偏离预案 1 项)
总分: 91/100
评级: 良好
```

#### 步骤 5：风险分级预警

**风险分级标准：**

| 风险等级 | 判定条件 | 建议动作 |
|----------|----------|----------|
| 低 | 核对全部通过，演练评分 ≥ 90 | 维持现状，定期复查 |
| 中 | 存在 1-2 项非关键缺失，评分 75-89 | 限期 1 周内整改 |
| 高 | 存在关键缺失或评分 60-74 | 立即整改，2 日内复查 |
| 严重 | 备份失败或评分 < 60 | 启动应急流程，当日处理 |

**输出示例：**

```
[风险预警] 等级: 高
风险描述: 数据库备份保留周期不足（当前 7 天，要求 ≥ 30 天）
建议动作: 调整备份策略，延长保留周期至 30 天，并在 2 日内完成复查
```

---

## 四、置信度门控

### 4.1 信息不足处理

当输入数据缺失关键字段或无法确认某项信息时，输出 `[需核实:字段名]` 占位符，不进行任何猜测或编造。

**示例：**

- 备份清单中缺少 `checksum` 字段 → 输出 `[需核实:checksum]`
- 恢复演练记录未提供 RTO 实际值 → 输出 `[需核实:RTO实际值]`

### 4.2 边界值说明

| 场景 | 处理方式 |
|------|----------|
| 输入文件为空 | 输出错误码 `E1001`，提示文件无有效数据 |
| 字段类型不匹配 | 输出错误码 `E1002`，提示字段类型错误 |
| 版本对比时无历史版本 | 输出错误码 `E2001`，提示无对比基准 |

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `E1001` | 输入文件为空 | "输入文件不包含任何有效数据，请检查文件内容" | 1. 确认文件路径正确；2. 检查文件是否被清空；3. 重新导出备份清单 |
| `E1002` | 字段类型错误 | "字段 [字段名] 类型应为 [期望类型]，实际为 [实际类型]" | 1. 检查源数据格式；2. 按规范修正字段类型；3. 重新运行 |
| `E1003` | 缺少必填字段 | "缺少必填字段 [字段名]，无法完成核对" | 1. 补充缺失字段；2. 确认数据源完整性；3. 重新运行 |
| `E2001` | 无对比基准 | "未找到可对比的历史版本，请提供基准版本信息" | 1. 确认历史备份是否存在；2. 提供正确的基准版本 ID；3. 重新运行 |
| `E3001` | 评分数据不完整 | "评分所需数据不完整，缺少 [维度] 相关记录" | 1. 补充演练记录；2. 确认评分卡字段齐全；3. 重新运行 |
| `E9001` | 环境不满足 | "Python 版本或依赖库不满足要求" | 1. 升级 Python 至 3.9+；2. 安装 openpyxl；3. 重新运行 `--selftest` |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 忽略环境预检 | 直接运行主命令，遇到依赖错误才排查 | 先执行 `--selftest`，确认环境就绪 |
| 输入数据不完整 | 用不完整的清单强行核对，导致结果偏差 | 先检查必填字段，缺失时补充数据或使用 `[需核实]` 占位 |
| 版本对比基准错误 | 随意选择对比版本，导致差异结果失真 | 确认对比基准版本的正确性，选择最近一次成功备份 |
| 评分标准不统一 | 不同人使用不同评分标准，结果不可比 | 统一使用本 Skill 的评分卡，确保一致性 |
| 风险预警后不跟进 | 输出预警后无后续动作，问题持续存在 | 按预警等级设定整改时限，并安排复查 |

### 6.2 反模式示例

**错误做法：**

```
用户: "帮我检查备份"
助手: "好的，备份检查完成，一切正常。"
```

**正确做法：**

```
用户: "帮我检查备份"
助手: "请提供备份清单文件路径。我将按以下流程执行：
1. 环境预检（Python 版本、openpyxl）
2. 加载备份清单
3. 核对覆盖率、保留周期、状态
4. 输出核对结果与风险预警
请确认输入文件路径。"
```

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 运行 data-backup-checklist --selftest 确认环境
2. 准备备份清单（CSV/JSON/Excel），确保必填字段齐全
3. 执行 data-backup-checklist --input <文件路径>
4. 查看输出报告，关注风险等级与建议动作
```

### 7.2 分层次阅读路径

#### 新手路径（首次使用）

1. 阅读「能力边界」了解适用范围
2. 阅读「触发方式」确认使用场景
3. 按「标准流程」步骤 1-2 完成环境预检与数据准备
4. 执行主命令，查看输出报告

#### 进阶路径（深度使用）

1. 阅读「标准流程」全部步骤，理解核对规则与评分标准
2. 熟悉「错误码体系」，掌握常见问题排查方法
3. 参考「FAQ 反模式」，避免常见操作误区
4. 结合「置信度门控」，理解数据不完整时的处理逻辑

---

## 八、命令行接口参考

### 8.1 命令格式

```bash
data-backup-checklist [选项] [参数]
```

### 8.2 可用选项

| 选项 | 说明 |
|------|------|
| `--selftest` | 执行环境自检（Python 版本、依赖库） |
| `--version` | 显示版本信息 |
| `--input <路径>` | 指定输入文件路径 |
| `--format <格式>` | 指定输入格式（csv/json/excel） |
| `--output <路径>` | 指定输出报告路径 |
| `--compare <基准版本>` | 指定版本对比的基准 |

### 8.3 版本信息

```bash
data-backup-checklist --version
# 输出: data-backup-checklist 1.0.0
```

---

## 九、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。本 Skill 提供的分析结果仅供参考，不构成任何形式的专业建议或保证。因使用本 Skill 导致的任何直接或间接损失，Skill 作者及贡献者不承担任何责任。

2. **禁止反向工程**：未经授权，不得对本 Skill 进行反向工程、反编译、反汇编或试图提取源代码。不得复制、修改、分发本 Skill 的实质性部分，除非获得明确书面许可。

3. **合规使用**：使用者应确保使用本 Skill 的行为符合当地法律法规及所在组织的规定。本 Skill 不应用于任何非法或未经授权的活动。

4. **数据安全**：使用者应对输入数据的合法性、准确性及安全性负责。本 Skill 不收集、存储或传输任何用户数据。

5. **协议更新**：本协议可能随时更新，更新后的协议将在本 Skill 文档中发布。继续使用本 Skill 即视为接受更新后的协议。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

本 Skill 采用 MIT 许可证发布。

### MIT License

```
MIT License

Copyright (c) 2024 林墨研

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并确认适用性。*

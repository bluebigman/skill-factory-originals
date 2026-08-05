---
slug: data-backup-checklist
name: data-backup-checklist
displayName: 备份核查 完整性校验 风险预警
description: 备份清单核对、版本差异追踪、恢复演练评分与风险分级预警。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: BackupGuardian
agent_created: true
trigger_words: ["data-backup-checklist", "备份检查", "备份核对", "备份完整性"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 备份核查 Skill 文档

本 Skill 由 AI 辅助生成，仅供参考。使用前请结合自身环境验证。

---

## 一、能力边界（一页纸速查卡）

### 能做什么

| 能力项 | 说明 | 输出示例 |
|--------|------|----------|
| 清单核对 | 解析备份清单，逐条核对必填字段 | 表格：文件路径、大小、时间戳、状态 |
| 版本差异 | 对比两个时间点的备份版本，列出新增/删除/修改 | 差异列表 + 变更统计 |
| 恢复演练评估 | 根据演练记录计算可恢复性评分 | 评分：良好（≥80）/ 一般（50-79）/ 较差（<50） |
| 风险分级预警 | 按严重程度输出风险提示 | 高/中/低三级预警列表 |
| 多格式输出 | 支持 Markdown 表格、JSON、自定义分隔符文本 | 按需选择 |

### 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行实际备份 | 本 Skill 仅做分析，不触发任何备份或恢复操作 |
| 不处理单字段输入 | 输入必须包含至少两项字段（如文件名+时间戳），否则无法有效处理 |
| 不识别非备份内容 | 普通文件列表会被过滤，并提示"未识别为备份记录" |
| 不保证数据安全 | 本 Skill 不提供任何数据完整性或安全性的绝对保证 |

### 适用对象

- 运维工程师：日常备份巡检
- 数据管理员：备份策略调整参考
- 自动化脚本：通过 JSON 输出对接 CI/CD 流程

---

## 二、触发方式

### 触发词

- 主触发词：`data-backup-checklist`
- 同义场景词：`备份检查`、`备份核对`、`备份完整性`

### 场景映射表

| 用户说（大白话） | 实际触发动作 |
|------------------|--------------|
| "帮我看看今天的备份有没有问题" | 解析备份清单 → 核对完整性 → 输出风险预警 |
| "对比一下昨天和今天的备份差异" | 版本比对 → 输出差异列表 |
| "上次恢复演练结果怎么样" | 恢复演练评估 → 输出评分和等级 |
| "把备份结果导出成 JSON" | 输出 JSON 格式结果 |

---

## 三、标准流程

### 前置条件

1. 输入内容须包含以下至少两项字段，否则无法有效处理：
   - 备份文件路径/名称
   - 备份时间戳
   - 文件大小
   - 校验值（如 MD5/SHA256）
   - 备份类型（全量/增量/差异）
   - 备份状态（成功/失败/进行中）

2. 输入格式支持：
   - 直接粘贴文本（每行一条记录）
   - 结构化 JSON 数组
   - CSV 格式（逗号分隔）

### 执行步骤

**步骤 1：收集输入并确认格式**

- 接收用户输入的备份清单文本
- 自动识别格式（纯文本/JSON/CSV）
- 若格式无法识别，提示用户重新输入

**步骤 2：解析关键字段**

- 从每条记录中提取字段：文件名、时间戳、大小、状态等
- 过滤非备份内容（如普通文件列表），标记为"未识别为备份记录"

**步骤 3：版本比对处理**

- 若输入包含两个时间点的数据，执行差异对比
- 输出：新增文件列表、删除文件列表、修改文件列表、变更统计

**步骤 4：恢复演练评估**

- 根据演练记录（如恢复成功率、恢复耗时）计算可恢复性评分
- 评分规则：
  - 良好：≥80 分
  - 一般：50-79 分
  - 较差：<50 分

**步骤 5：生成风险预警报告**

- 按严重程度分级：
  - 高风险：备份失败、文件缺失、校验值不匹配
  - 中风险：备份延迟、大小异常、版本缺失
  - 低风险：备份策略建议（如增加频率）

**步骤 6：输出结果并自查**

- 按用户指定格式输出（默认 Markdown 表格）
- 自查：检查输出是否包含所有必填字段，是否有遗漏或错误

### 输出规范

| 输出格式 | 适用场景 | 示例 |
|----------|----------|------|
| Markdown 表格 | 人工阅读 | 见下方示例 |
| JSON | 自动化脚本对接 | `{"status":"ok","records":[...]}` |
| 自定义分隔符文本 | 日志系统 | `文件名|时间戳|大小|状态` |

---

## 四、置信度门控

当输入信息不足时，本 Skill 不会编造数据，而是输出占位符 `[需核实:字段名]`。

| 场景 | 输出示例 |
|------|----------|
| 缺少文件大小 | `[需核实:文件大小]` |
| 缺少备份时间 | `[需核实:备份时间]` |
| 缺少校验值 | `[需核实:校验值]` |

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 输入为空 | "未检测到输入内容，请粘贴备份清单或上传文件" | 重新输入备份清单 |
| E002 | 字段不足 | "输入内容字段不足，至少需要两项字段（如文件名+时间戳）" | 补充字段后重新输入 |
| E003 | 格式无法识别 | "无法识别输入格式，请使用纯文本、JSON 或 CSV 格式" | 转换格式后重新输入 |
| E004 | 非备份内容 | "未识别为备份记录，已过滤非备份内容" | 确认输入内容后重试 |
| E005 | 版本比对失败 | "版本比对需要两个时间点的数据，请补充历史备份记录" | 补充数据后重新执行 |

---

## 六、FAQ 反模式

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 输入不完整 | 只给一个文件名就要求分析 | 至少提供文件名+时间戳+大小 |
| 忽略格式要求 | 随意粘贴混合格式文本 | 统一为一种格式（纯文本/JSON/CSV） |
| 期望执行备份 | 要求"帮我备份一下" | 本 Skill 仅做分析，不执行备份操作 |
| 忽略置信度提示 | 把 `[需核实:字段]` 当作真实数据 | 根据提示补充信息后重新分析 |
| 过度依赖评分 | 仅凭评分决定备份策略 | 结合业务场景和风险预警综合判断 |

---

## 七、渐进式披露

### 速查卡（30 秒上手）

1. 输入备份清单（至少两项字段）
2. 说出触发词 `data-backup-checklist`
3. 获取 Markdown 核对结果和风险提示

### 新手路径（5 分钟）

1. 阅读"能力边界"了解适用范围
2. 按"标准流程"步骤 1-2 准备输入
3. 查看输出表格中的状态列和风险列
4. 如有疑问，参考"FAQ 反模式"排查问题

### 进阶路径（深度使用）

1. 使用 JSON 输出格式对接自动化脚本
2. 利用版本比对功能追踪多日备份连续性
3. 根据恢复演练评分调整备份策略（如增加频率或校验）
4. 结合错误码体系排查自动化流程中的异常

---

## 八、示例

### 输入示例

```
backup_20240101.tar.gz, 2024-01-01 02:00:00, 1.2GB, success, full
backup_20240102.tar.gz, 2024-01-02 02:00:00, 1.3GB, success, full
backup_20240103.tar.gz, 2024-01-03 02:00:00, 1.1GB, failed, full
```

### 输出示例（Markdown）

| 文件名 | 时间戳 | 大小 | 状态 | 类型 | 风险等级 |
|--------|--------|------|------|------|----------|
| backup_20240101.tar.gz | 2024-01-01 02:00:00 | 1.2GB | 成功 | 全量 | 低 |
| backup_20240102.tar.gz | 2024-01-02 02:00:00 | 1.3GB | 成功 | 全量 | 低 |
| backup_20240103.tar.gz | 2024-01-03 02:00:00 | 1.1GB | 失败 | 全量 | **高** |

**风险预警：**
- 高风险：2024-01-03 备份失败，请立即检查备份任务
- 建议：连续 2 天备份成功，可考虑每周做一次恢复演练

---

## 用户协议

<!-- user-agreement-injected -->

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。本 Skill 仅提供分析建议，不构成任何数据安全保证。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码。
3. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性。
4. **使用限制**：不得将本 Skill 用于任何违法或未经授权的目的。

---

## 许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 BackupGuardian

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

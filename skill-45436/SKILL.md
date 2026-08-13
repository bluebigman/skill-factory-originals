---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: skill-45436
name: skill-45436
displayName: 数据清洗 表格整理 格式校验
description: 一站式数据整理技能，覆盖识别、清洗、生成与校验，输出可直接使用的干净文件。
version: 1.0.1
rules_version: cpr-20260813-n401
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/skill-45436
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataCraft Studio
agent_created: true
trigger_words: ["数据整理", "洗数据", "表格清洗", "数据去重", "格式统一", "缺失值处理"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 数据清洗与整理 Skill 文档

## 一、能力边界（一页纸速查卡）

本 Skill 专注于**结构化数据文件**的整理与清洗，不涉及数据采集、建模或可视化分析。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 文件格式 | Excel（.xlsx/.xls）、CSV、JSON | 数据库直连、PDF 表格抽取、图片 OCR |
| 核心操作 | 去重、格式统一、缺失值处理、多文件合并 | 数据透视、图表生成、机器学习建模 |
| 输出形式 | 清洗后的文件 + 质量报告（Markdown） | 可视化仪表盘、API 服务部署 |
| 数据规模 | 单文件 ≤ 50 万行，多文件合并 ≤ 10 个 | 流式数据、实时同步 |
| 编码处理 | UTF-8、GBK、GB2312 自动识别 | 加密文件、二进制格式 |

**适用对象**：需要快速处理中小规模表格数据的运营人员、数据分析师、业务管理者。不适用于需要复杂业务规则编排的场景。

---

## 二、触发方式

### 触发词

- 主触发词：`数据整理`、`洗数据`、`表格清洗`
- 辅助触发词：`数据去重`、`格式统一`、`缺失值处理`、`合并表格`

### 场景映射表

| 用户说（大白话） | 实际需求 | 触发动作 |
|------------------|----------|----------|
| "帮我洗下表格" | 数据去重 + 格式统一 | 启动完整清洗流程 |
| "这个表里有重复的，帮我删掉" | 按指定列去重 | 执行去重操作 |
| "日期格式乱七八糟的" | 统一日期格式 | 执行格式标准化 |
| "有些格子是空的怎么办" | 缺失值处理 | 按策略填充或标记 |
| "把三个表合成一个" | 多文件合并 | 执行合并操作 |

---

## 三、标准流程

### 前置条件

1. 文件可访问：本地路径或已上传的文件
2. 文件格式支持：Excel/CSV/JSON
3. 用户明确或可推断清洗目标

### 执行步骤

**Step 1：信息确认（必选）**

| 参数 | 说明 | 示例 |
|------|------|------|
| 文件路径 | 文件所在位置 | `/data/orders.csv` |
| 清洗目标 | 去重/格式/缺失值/合并/全部 | 全部 |
| 特殊要求 | 去重列、填充策略等 | 按订单号去重，缺失金额填 0 |

**Step 2：文件预检（自动）**

- 读取文件头 50 行，检测编码格式
- 识别列名、数据类型、行数
- 输出预检摘要，与用户确认

**Step 3：执行清洗（按需组合）**

```python
# 示例：去重 + 缺失值处理
import pandas as pd

df = pd.read_csv("input.csv", encoding="utf-8")
df = df.drop_duplicates(subset=["order_id"], keep="first")
df["amount"] = df["amount"].fillna(0)
df.to_csv("output_cleaned.csv", index=False, encoding="utf-8-sig")
```

**Step 4：质量校验（自动）**

- 对比清洗前后行数、缺失值数量
- 检查数据类型一致性
- 生成质量报告

**Step 5：输出交付**

- 清洗后文件（与原格式一致）
- 质量报告（Markdown 格式，含清洗前后对比）

### 输出规范

| 输出项 | 格式 | 内容 |
|--------|------|------|
| 数据文件 | 与原文件相同格式 | 清洗后的完整数据 |
| 质量报告 | Markdown | 清洗规则、影响行数、剩余问题 |

---

## 四、置信度门控

当信息不足时，**不猜测、不编造**，使用 `[需核实:字段名]` 占位。

**常见信息缺失场景：**

| 场景 | 处理方式 |
|------|----------|
| 未指定去重列 | 输出 `[需核实:去重列]`，询问用户 |
| 缺失值填充策略不明确 | 默认标记为 `[需核实:缺失值策略]`，不自动填充 |
| 日期格式目标不明确 | 保持原格式，标注 `[需核实:目标日期格式]` |
| 合并键未指定 | 输出 `[需核实:合并键]`，不执行合并 |

**示例对话：**

> 用户：帮我洗下这个表
> AI：请提供文件路径，并确认清洗目标（去重/格式/缺失值/合并/全部）。另外，去重需要按哪一列？缺失值希望怎么处理？

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 文件路径不存在 | "未找到指定文件，请确认路径是否正确" | 检查路径拼写，或重新上传文件 |
| E002 | 编码识别失败 | "无法自动识别文件编码" | 手动指定编码（UTF-8/GBK/GB2312） |
| E003 | 格式不支持 | "仅支持 Excel/CSV/JSON 格式" | 转换文件格式后重试 |
| E004 | 列名不存在 | "指定的列 [列名] 在文件中不存在" | 查看预检摘要，确认正确列名 |
| E005 | 数据量超限 | "文件行数超过 50 万行限制" | 拆分文件或抽样处理 |
| E006 | 合并键冲突 | "合并时发现重复键，可能导致数据膨胀" | 确认合并策略（保留全部/去重） |

---

## 六、FAQ 反模式

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 盲目去重 | 不指定列，全行去重 | 明确指定去重列，避免误删有效数据 |
| 缺失值一刀切 | 所有缺失值填 0 | 区分数值列和文本列，分别处理 |
| 日期格式混乱 | 直接字符串替换 | 使用 `pd.to_datetime()` 统一转换 |
| 合并时忽略编码 | 直接 concat 报错 | 先统一编码，再执行合并 |
| 忽略数据质量报告 | 只看结果文件 | 仔细阅读质量报告，确认清洗效果 |

---

## 七、渐进式披露

### 速查卡（30 秒上手）

```
输入：文件路径 + 清洗目标 + 特殊要求
输出：清洗后文件 + 质量报告
支持格式：Excel / CSV / JSON
限制：单文件 ≤ 50 万行，合并 ≤ 10 个文件
```

### 新手路径（首次使用）

1. 准备一个 CSV 文件（建议 ≤ 1 万行）
2. 说"帮我洗下表格"，提供文件路径
3. 回答 AI 的确认问题（清洗目标、特殊要求）
4. 等待输出，查看质量报告

### 进阶路径（熟练用户）

1. 批量处理多个文件，使用合并功能
2. 自定义缺失值填充策略（均值/中位数/前向填充）
3. 指定多列去重规则
4. 结合质量报告，迭代优化清洗规则

---

## 八、CLI 接口说明

```bash
# 自检命令
数据整理 --selftest

# 版本查询
数据整理 --version
```

`--selftest` 会执行内部测试用例，验证核心功能可用性。`--version` 输出当前版本号。

---

## 用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于数据丢失、数据错误、业务损失等。
2. **数据安全**：使用者应确保输入数据不包含敏感信息（如个人隐私、商业机密）。本 Skill 不承担数据泄露责任。
3. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码。
4. **合规使用**：使用者应确保数据处理行为符合当地法律法规。
5. **无担保**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

---

## 许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 DataCraft Studio

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*

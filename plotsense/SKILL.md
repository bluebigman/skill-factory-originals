---
slug: plotsense
name: plotsense
displayName: 数据洞察 图表感知 结构解析
description: 将数据、文件或URL转化为结构化结果，识别关键信息并标注置信度。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 知微
agent_created: true
trigger_words: ["plotsense", "图表感知", "数据解析", "结构化输出", "信息提取"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# plotsense — 数据感知与结构化输出 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做（5项核心能力）

| 序号 | 能力项 | 说明 | 适用场景示例 |
|------|--------|------|--------------|
| 1 | 数据/文件/URL 转结构化结果 | 将输入内容解析为字段化、可复用的结构化数据 | 从 CSV 提取字段、从网页提取表格 |
| 2 | 关键信息识别与保留 | 自动识别输入中的核心实体、数值、关系，并保留上下文 | 从报告中提取日期、金额、责任人 |
| 3 | 按约定格式生成输出 | 遵循用户指定的输出模板或默认 schema 输出 | 输出 JSON、Markdown 表格、键值对 |
| 4 | 置信度提示 | 对每个输出字段标注置信度等级（高/中/低） | 识别模糊字段时标注"中置信度" |
| 5 | 批量处理与自定义格式 | 支持多文件/多 URL 批量执行，支持自定义输出模板 | 批量解析 100 个日志文件 |

### 1.2 不能做（明确边界）

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行代码 | 本 Skill 不运行 Python/Shell 等代码，仅做文本解析与结构转换 |
| 2 | 不访问付费/登录墙内容 | 无法解析需要认证或付费的 URL 内容 |
| 3 | 不做语义推理 | 不进行因果推断、趋势预测等高级分析 |
| 4 | 不修改原始文件 | 所有操作均为只读，输出为独立结果文件 |
| 5 | 不保证 100% 准确 | 对模糊输入会标注置信度，不承诺绝对正确 |

### 1.3 适用对象

- 需要快速将非结构化数据转为结构化格式的开发者
- 需要批量提取文档/URL 中关键字段的运营人员
- 需要统一数据格式以便入库或分析的数据工程师

---

## 二、触发方式

### 2.1 触发词

使用以下任一关键词即可激活本 Skill：

- `plotsense`
- `图表感知`
- `数据解析`
- `结构化输出`
- `信息提取`
- `字段提取`

### 2.2 场景映射表

| 用户说（大白话） | 实际触发动作 |
|------------------|--------------|
| "帮我把这个 CSV 转成 JSON" | 解析 CSV → 输出 JSON 结构化数据 |
| "从这个网页里提取所有价格信息" | 抓取 URL → 提取价格字段 → 结构化输出 |
| "把这三个日志文件的错误码都列出来" | 批量解析日志 → 提取错误码字段 |
| "这个报告里的日期和金额帮我整理一下" | 解析文档 → 提取日期+金额 → 表格输出 |
| "按我给的模板输出结果" | 读取用户模板 → 按模板字段映射输出 |

---

## 三、标准流程

### 3.1 前置条件

| 条件项 | 要求 |
|--------|------|
| 输入文件 | 与 Skill 运行目录一致，命名规范统一（如 `input_001.csv`） |
| 输入格式 | 支持：CSV、JSON、TXT、Markdown、HTML（URL） |
| 输出模板（可选） | 用户可提供自定义字段映射模板 |
| 运行环境 | 无需特殊依赖，纯文本处理 |

### 3.2 执行步骤

#### 步骤 1：准备输入

1. 将待处理文件放入当前工作目录。
2. 确认文件命名规范一致（如 `data_01.csv`、`data_02.csv`）。
3. 若输入为 URL，确认链接可公开访问。

#### 步骤 2：试运行（单样本验证）

1. 选取 1 个样本文件执行解析。
2. 核对输出字段是否完整、格式是否正确。
3. 若输出不符合预期，调整解析规则或模板。

#### 步骤 3：批量执行

1. 确认试运行无误后，对全量数据执行。
2. 保留原始文件备份（建议复制到 `backup/` 目录）。
3. 输出结果文件命名规则：`output_<原文件名>.json`。

#### 步骤 4：校验结果

1. 抽查 10% 输出条目。
2. 核对关键字段（如 ID、日期、金额）与源数据一致性。
3. 对置信度标注为"低"的字段进行人工复核。

### 3.3 输出规范

#### 默认输出格式（JSON）

```json
{
  "source": "input_001.csv",
  "parsed_at": "2025-01-15T10:30:00Z",
  "record_count": 3,
  "records": [
    {
      "id": "001",
      "date": "2025-01-10",
      "amount": 1234.56,
      "confidence": {
        "id": "high",
        "date": "high",
        "amount": "medium"
      }
    }
  ]
}
```

#### 字段置信度等级

| 等级 | 含义 | 适用条件 |
|------|------|----------|
| high | 明确无误 | 字段值完整、格式标准、无歧义 |
| medium | 基本可信 | 字段值存在轻微格式差异或上下文模糊 |
| low | 需人工确认 | 字段缺失、格式异常、存在多义性 |

#### 自定义输出模板

用户可提供模板文件 `template.json`：

```json
{
  "field_mapping": {
    "原字段名": "目标字段名"
  },
  "output_format": "json|markdown|csv"
}
```

---

## 四、置信度门控

### 4.1 原则

**不编造、不猜测、不补全。** 当信息不足时，使用占位符 `[需核实:字段名]` 标记，并标注置信度为 `low`。

### 4.2 触发条件

| 场景 | 处理方式 |
|------|----------|
| 字段缺失 | 输出 `[需核实:字段名]`，置信度 `low` |
| 字段格式异常 | 保留原始值，标注 `[需核实:字段名]`，置信度 `low` |
| 字段值存在多义性 | 输出最可能值，标注 `[需核实:字段名]`，置信度 `medium` |
| 无法解析的输入 | 返回错误码 `E1001`，不输出部分结果 |

### 4.3 示例

输入：`日期：2025/1/10，金额：约1200元`

输出：

```json
{
  "date": "2025-01-10",
  "amount": "[需核实:amount]",
  "confidence": {
    "date": "high",
    "amount": "low"
  }
}
```

---

## 五、错误码体系

| 错误码 | 含义 | 用户提示话术 | 修正步骤 |
|--------|------|--------------|----------|
| E1001 | 输入不可解析 | "无法识别输入内容，请检查文件格式或 URL 有效性。" | 1. 确认文件非空且格式正确；2. 确认 URL 可公开访问 |
| E1002 | 字段映射冲突 | "模板字段映射存在冲突，请检查 template.json。" | 1. 检查映射是否有重复目标字段；2. 删除冲突映射 |
| E1003 | 批量处理中断 | "批量处理在第 N 个文件处中断，请检查该文件。" | 1. 定位失败文件；2. 单独执行该文件排查问题 |
| E1004 | 输出目录不可写 | "无法写入输出文件，请检查目录权限。" | 1. 确认目录存在；2. 修改目录写权限 |
| E1005 | 置信度过低 | "输出结果中超过 30% 字段置信度为 low，建议人工复核。" | 1. 检查源数据质量；2. 调整解析规则 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式（错误做法） | 正确做法 |
|----|-------------------|----------|
| 忽略试运行 | 直接跑全量数据，结果格式全错 | 先跑 1 个样本，确认格式后再批量 |
| 覆盖原始文件 | 输出直接覆盖输入文件 | 保留原始文件，输出到独立目录 |
| 编造缺失字段 | 对缺失字段随意补默认值 | 使用 `[需核实:字段]` 占位，标注 low 置信度 |
| 忽略置信度 | 所有字段一律标 high | 根据实际解析情况如实标注 |
| 不校验结果 | 输出后直接交付，不抽查 | 至少抽查 10% 输出与源数据比对 |

### 6.2 反模式对照表

| 场景 | 反模式 | 正模式 |
|------|--------|--------|
| 用户要求"直接给我结果" | 跳过试运行直接全量处理 | 先说明试运行必要性，快速跑 1 个样本 |
| 用户说"这个字段肯定有" | 强行补全缺失字段 | 如实标注 `[需核实:字段]` |
| 用户要求"把所有数字都提取" | 无差别提取所有数字 | 先确认数字的业务含义，再按字段提取 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 放文件 → 2. 跑 1 个样本 → 3. 核对输出 → 4. 批量跑 → 5. 抽查结果
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」了解能做什么。
2. 按「标准流程」步骤 1-2 完成单样本测试。
3. 确认输出格式符合预期后，再执行批量。
4. 遇到问题查「错误码体系」。

### 7.3 进阶路径（熟练用户）

1. 自定义 `template.json` 实现字段映射。
2. 使用批量处理时，预先规划好文件命名规范。
3. 对低置信度字段建立人工复核流程。
4. 结合错误码 E1005 设置置信度阈值告警。

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的输出仅供参考，不构成任何形式的保证或承诺。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取底层算法。
3. **合法使用**：使用者须确保输入数据来源合法，不得使用本 Skill 处理违法违规内容。
4. **无担保**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2025 知微

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

*本 Skill 由 AI 辅助生成，仅供学习参考。使用前请阅读相关文档。*

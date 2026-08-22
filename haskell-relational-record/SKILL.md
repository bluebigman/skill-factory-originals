---
slug: haskell-relational-record
name: haskell-relational-record
displayName: 关系记录处理 数据转换 类型安全
description: 将输入数据转换为结构化结果，保留关键信息并标注置信度，支持批量处理。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: skill-forge-studio
agent_created: true
trigger_words: ["haskell-relational-record", "关系记录处理", "数据转换", "结构化输出", "批量处理"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# haskell-relational-record 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入处理 | 接受用户提供的数据、文件、URL 作为输入源 | 不接受二进制文件或加密数据 |
| 信息提取 | 识别并保留输入中的关键信息字段 | 不推断输入中未明确表达的信息 |
| 输出生成 | 按约定格式生成结构化结果，支持自定义格式 | 不生成非结构化或自由文本输出 |
| 置信度标注 | 对每个输出字段标注置信度等级 | 不提供无置信度标注的输出 |
| 批量处理 | 支持多文件批量处理与统一格式输出 | 不支持跨批次数据关联分析 |

### 1.2 适用对象

- 需要将原始数据转换为结构化记录的开发者
- 需要批量处理数据文件并保持格式一致性的运维人员
- 需要从 URL 抓取信息并生成规范输出的数据分析师

### 1.3 输入输出规格

| 项目 | 规格 |
|------|------|
| 输入来源 | 用户提供的数据、文件（.txt/.csv/.json）、URL |
| 输出格式 | JSON 结构化对象，含 `data` 与 `confidence` 字段 |
| 字段结构 | `{ "key": value, "confidence": 0.0-1.0 }` |
| 处理单元 | 单条记录或批量记录（≤1000条/批次） |

---

## 二、触发方式

### 2.1 触发词

- 主触发词：`haskell-relational-record`
- 同义场景词：`关系记录处理`、`数据转换`、`结构化输出`、`批量处理`

### 2.2 场景映射表

| 用户说（大白话） | 实际触发动作 |
|------------------|--------------|
| "帮我把这个 CSV 转成结构化记录" | 解析 CSV → 生成 JSON 结构化输出 |
| "这个 URL 里的数据帮我提取一下" | 抓取 URL → 提取关键信息 → 结构化输出 |
| "这批文件统一处理一下" | 批量读取文件 → 逐条转换 → 汇总输出 |
| "输出格式要自定义" | 按用户指定字段结构生成输出 |

---

## 三、标准处理流程

### 3.1 前置条件

1. 输入文件与技能运行目录一致，命名遵循 `input_*.csv` 或 `data_*.json` 规范
2. 输入数据编码为 UTF-8，避免特殊字符导致解析失败
3. 确认输出目录存在且有写入权限

### 3.2 执行步骤

| 步骤 | 操作 | 说明 |
|------|------|------|
| 1 | 准备输入 | 将待处理文件放入指定目录，确认命名规范一致 |
| 2 | 试运行 | 先用单个样本执行，核对输出字段与格式是否符合预期 |
| 3 | 批量执行 | 确认无误后对全量数据执行，保留原始文件备份 |
| 4 | 校验结果 | 抽查输出条目，核对关键字段与源数据一致性 |

### 3.3 输出规范

```json
{
  "record_id": "001",
  "data": {
    "field_a": "value_a",
    "field_b": "value_b"
  },
  "confidence": 0.95
}
```

- `confidence` 取值范围：`0.0`（完全不确定）至 `1.0`（完全确定）
- 置信度低于 `0.6` 时，输出中附加 `"warning": "low_confidence"` 标记

---

## 四、置信度门控

### 4.1 置信度判定规则

| 场景 | 置信度 | 处理方式 |
|------|--------|----------|
| 字段值直接提取，无歧义 | 0.9-1.0 | 正常输出 |
| 字段值需格式转换或映射 | 0.7-0.89 | 正常输出，附加转换说明 |
| 字段值缺失或格式异常 | 0.4-0.69 | 输出 `[需核实:字段名]` 占位符 |
| 字段值完全无法确定 | 0.0-0.39 | 输出 `[需核实:字段名]`，附加错误码 |

### 4.2 信息不足处理

当输入信息不足以确定某个字段值时：

1. 不编造数据，输出 `[需核实:字段名]` 占位符
2. 在输出末尾附加 `"unresolved_fields": ["字段名1", "字段名2"]`
3. 提示用户补充缺失信息后重新处理

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入文件不存在 | "未找到指定输入文件，请检查路径" | 确认文件路径，重新放置文件 |
| `E002` | 输入格式无法解析 | "输入格式不符合预期，请检查文件编码与结构" | 转换文件编码为 UTF-8，修正格式 |
| `E003` | 输出目录无写入权限 | "无法写入输出目录，请检查权限设置" | 修改目录权限或更换输出路径 |
| `E004` | 批量处理中途失败 | "批量处理在第 N 条记录处失败" | 定位失败记录，单独处理该条 |
| `E005` | 置信度低于阈值 | "部分字段置信度低于 0.6，请核实" | 检查源数据，补充缺失信息 |

---

## 六、FAQ 反模式对照

### 6.1 常见坑与正确做法

| 常见坑（反模式） | 正确做法 |
|------------------|----------|
| 直接对全量数据执行，不做试运行 | 先单样本试运行，确认格式后再批量 |
| 覆盖原始文件，不做备份 | 保留原始文件备份，输出到独立目录 |
| 对缺失字段自行猜测填充 | 输出 `[需核实:字段名]` 占位符，不编造 |
| 忽略置信度标注 | 每个输出字段必须附带置信度 |
| 批量处理中途失败后从头重跑 | 定位失败记录，从失败点继续处理 |

### 6.2 反模式示例

**反模式**：用户提供 1000 条记录，直接全量处理，结果第 500 条格式错误导致全部失败。

**正确做法**：
1. 先取 1 条样本试运行，确认输出格式
2. 批量执行时，每 100 条设置检查点
3. 失败时定位到具体记录，修正后从检查点继续

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
输入 → 试运行 → 批量执行 → 校验输出
```

- 输入文件命名：`input_*.csv`
- 输出格式：JSON 含 `data` 与 `confidence`
- 置信度低于 0.6：输出 `[需核实:字段名]`
- 错误码：`E001`-`E005`

### 7.2 新手路径（首次使用）

1. 阅读能力边界，确认技能适用范围
2. 准备单个样本文件，执行试运行
3. 核对输出格式与置信度标注
4. 确认无误后，按标准流程批量处理

### 7.3 进阶路径（熟练使用）

1. 自定义输出字段结构，适配特定业务场景
2. 利用置信度门控机制，自动标记低质量数据
3. 结合错误码体系，建立自动化异常处理流程
4. 对批量处理设置检查点，实现断点续跑

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本技能即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本技能产生的全部责任。本技能提供的输出仅供参考，不构成任何形式的保证或承诺。
2. **禁止反向工程**：不得对本技能进行反向工程、反编译、破解或试图提取底层算法。
3. **合规使用**：使用者应确保输入数据的合法性与合规性，不得使用本技能处理违法违规内容。
4. **免责声明**：本技能按"原样"提供，不附带任何明示或暗示的保证。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

### MIT License

```
MIT License

Copyright (c) 2024 skill-forge-studio

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*

---
slug: markaby
name: markaby
displayName: 数据解析 结构化提取 批量转换
description: 将用户输入数据解析为结构化结果，标注置信度并支持批量处理。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataFlow Studio
agent_created: true
trigger_words: ["markaby", "数据解析", "结构化输出", "信息提取", "批量转换", "字段抽取", "数据清洗"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# markaby — 数据解析与结构化输出 Skill

本 Skill 由 AI 辅助生成，仅供参考。使用前请结合自身数据场景验证输出质量。

---

## 一、能力边界（一页纸速查卡）

### ✅ 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 单条数据解析 | 从一段文本/记录中抽取关键字段 | 从订单号+日期+金额的混合文本中拆出三个字段 |
| 批量数据转换 | 对同一目录下多个文件执行相同解析逻辑 | 将 100 个 `.txt` 记录统一转为结构化 JSON |
| 置信度标注 | 对每个输出字段给出可信程度标记 | `confidence: 0.95` 或 `[需核实:字段名]` |
| 格式校验 | 核对输出字段与源数据的一致性 | 日期格式、金额精度、编号规则 |

### ❌ 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不处理非文本文件 | 图片、PDF 扫描件需先 OCR 转文本 |
| 不自动修复源数据 | 源数据缺失或错误时，仅标注不篡改 |
| 不跨目录搜索 | 仅处理当前工作目录下符合命名规则的文件 |
| 不保证 100% 准确 | 复杂语义或歧义文本需人工复核 |

### 🎯 适用对象

- 需要将非结构化文本转为表格/JSON 的数据处理人员
- 需要批量清洗日志、订单、客户信息的运营人员
- 需要为下游系统准备标准化输入的开发人员

---

## 二、触发方式

### 触发词

直接使用以下任一关键词即可激活本 Skill：

- `markaby`
- `数据解析`
- `结构化输出`
- `信息提取`
- `批量转换`
- `字段抽取`
- `数据清洗`

### 场景映射表

| 你说的话（大白话） | 实际执行动作 |
|-------------------|-------------|
| "帮我把这些订单记录整理成表格" | 解析每条记录中的订单号、日期、金额字段 |
| "这个文件夹里的日志能转成 JSON 吗" | 批量读取目录下所有日志文件，输出结构化 JSON |
| "这些客户信息太乱了，帮我理一理" | 抽取姓名、电话、邮箱等字段并标注置信度 |
| "跑一下看看结果对不对" | 用单个样本执行试运行，输出字段对照表 |

---

## 三、标准流程

### 前置条件

1. 待处理文件已放入当前工作目录
2. 文件命名遵循统一规范（如 `data_001.txt`、`data_002.txt`）
3. 已确认源数据编码格式（UTF-8 优先）

### 执行步骤

#### 第 1 步：准备输入

- 将待处理文件放入同一目录
- 检查命名规范是否一致（建议格式：`前缀_序号.扩展名`）
- 确认文件编码（默认 UTF-8，如有特殊编码需提前说明）

#### 第 2 步：试运行（单样本验证）

- 选取 1 个代表性文件执行解析
- 核对输出字段是否完整、格式是否符合预期
- 检查置信度标注是否合理

**试运行输出示例：**

```json
{
  "source_file": "data_001.txt",
  "parsed_fields": {
    "order_id": "ORD-2024-001",
    "date": "2024-03-15",
    "amount": 1299.00
  },
  "confidence": {
    "order_id": 0.98,
    "date": 0.95,
    "amount": 0.99
  },
  "warnings": []
}
```

#### 第 3 步：批量执行

- 确认试运行结果无误后，对全量数据执行
- 保留原始文件备份（自动生成 `backup/` 目录）
- 输出文件按 `parsed_原文件名.json` 命名

#### 第 4 步：校验结果

- 随机抽查 5%-10% 的输出条目
- 核对关键字段（如订单号、日期、金额）与源数据一致
- 对置信度低于 0.8 的字段进行人工复核

### 输出规范

| 输出项 | 格式 | 说明 |
|--------|------|------|
| 解析结果 | JSON 文件 | 每个源文件对应一个输出文件 |
| 汇总报告 | `summary_report.json` | 包含总处理数、成功数、失败数、平均置信度 |
| 错误日志 | `error_log.txt` | 记录解析失败的条目及原因 |

---

## 四、置信度门控

### 基本原则

- **不编造**：源数据中不存在或无法推断的字段，输出 `[需核实:字段名]` 占位
- **不猜测**：当字段含义存在歧义时，降低置信度并添加警告
- **可追溯**：每个输出字段均可回溯到源数据位置

### 置信度等级

| 等级 | 分值范围 | 含义 | 处理建议 |
|------|----------|------|----------|
| 高 | 0.90 - 1.00 | 字段明确，无歧义 | 可直接使用 |
| 中 | 0.70 - 0.89 | 字段可推断，但存在少量不确定性 | 建议人工抽查 |
| 低 | 0.50 - 0.69 | 字段模糊，需人工确认 | 必须人工复核 |
| 不足 | < 0.50 | 无法判断 | 输出 `[需核实:字段名]` |

### 信息不足时的处理

当遇到以下情况，输出 `[需核实:字段名]` 占位：

- 源数据中字段缺失
- 字段格式不符合预期（如日期格式混乱）
- 多个可能值无法确定唯一答案

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件不存在 | "未找到指定文件，请检查路径和文件名" | 1. 确认文件路径正确 2. 检查文件名拼写 3. 确认文件已放入工作目录 |
| `E002` | 文件格式不支持 | "仅支持 .txt、.csv、.json 格式文件" | 1. 转换文件格式 2. 或提供文件内容预览 |
| `E003` | 编码错误 | "文件编码无法识别，请确认为 UTF-8" | 1. 使用文本编辑器转换编码 2. 重新保存为 UTF-8 |
| `E004` | 字段解析失败 | "第 X 行字段无法解析，请检查源数据" | 1. 查看源数据对应行 2. 手动修正格式 3. 重新执行 |
| `E005` | 批量处理中断 | "处理过程中断，已保留已处理结果" | 1. 查看 error_log.txt 2. 修复问题后重新执行 |
| `E006` | 输出目录无权限 | "无法写入输出目录，请检查权限" | 1. 修改目录权限 2. 或更换输出路径 |

---

## 六、FAQ 反模式

### 常见坑 1：跳过试运行直接批量执行

**反模式**：拿到数据直接跑全量，结果发现字段映射错误，全部返工。

**正确做法**：始终先用单个样本试运行，确认字段和格式无误后再批量执行。

### 常见坑 2：忽略置信度标注

**反模式**：只关注解析结果，不看置信度，导致低质量数据进入下游系统。

**正确做法**：对置信度低于 0.8 的字段设置人工复核流程。

### 常见坑 3：修改源数据文件

**反模式**：在解析过程中直接修改原始文件，导致无法追溯和重跑。

**正确做法**：始终保留原始文件，所有修改写入输出文件。

### 常见坑 4：命名不规范导致漏处理

**反模式**：文件命名混乱（如 `新建文档(1).txt`），导致部分文件未被识别。

**正确做法**：执行前统一重命名，遵循 `前缀_序号.扩展名` 规范。

### 常见坑 5：忽略错误日志

**反模式**：批量执行后只看成功结果，忽略 error_log.txt 中的失败条目。

**正确做法**：每次执行后检查错误日志，确保所有条目均被正确处理。

---

## 七、渐进式披露

### 🚀 速查卡（30 秒上手）

```
1. 放文件 → 2. 跑单样本 → 3. 查字段 → 4. 跑批量 → 5. 抽查结果
```

### 📖 新手路径（首次使用）

1. 阅读「能力边界」了解适用范围
2. 按「标准流程」第 1-2 步准备并试运行
3. 对照「输出规范」检查结果
4. 遇到问题查「错误码体系」

### 🔧 进阶路径（熟练用户）

1. 深入理解「置信度门控」机制，优化人工复核策略
2. 结合「FAQ 反模式」规避常见陷阱
3. 根据「错误码体系」建立自动化错误处理流程
4. 自定义字段映射规则，适配特定业务场景

---

## 用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。包括但不限于数据解析结果准确性、数据安全性及合规性。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取底层算法。
3. **数据合规**：使用者需确保输入数据不违反任何法律法规，不包含敏感个人信息（除非已获得合法授权）。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。
5. **免责范围**：因使用本 Skill 导致的任何直接或间接损失，Skill 作者不承担任何责任。

---

## 许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 DataFlow Studio

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

*本 Skill 文档由 AI 辅助生成，用于提供数据解析与结构化输出的操作指导。使用前请结合具体场景验证适用性。*

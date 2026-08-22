---
slug: commonocrextractor
name: commonocrextractor
displayName: 票据识别 模板定制 字段抽取
description: 可视化OCR模板定制与结构化数据抽取工具，支持票据后处理与mask矫正。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["commonocrextractor", "OCR模板", "票据识别", "字段抽取", "结构化数据", "mask矫正", "票据后处理"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# commonocrextractor — 可视化OCR模板定制与结构化抽取

## 一、能力边界速查卡

本 Skill 面向需要从票据、证照、单据等半结构化文档中提取关键字段的场景，提供模板定制、字段抽取、后处理矫正的能力。

| 维度 | 说明 |
|------|------|
| **核心输入** | 图片文件（PNG/JPG/JPEG/BMP/TIFF）、PDF 单页、可访问的图片 URL |
| **核心输出** | JSON 结构化字段集合，含字段名、字段值、置信度、坐标框 |
| **支持能力** | 模板可视化标注、字段类型推断、OCR 结果后处理、mask 区域矫正、批量文件处理 |
| **不支持能力** | 手写体自由文本理解、非固定版式文档的语义解析、跨页上下文关联、模型训练 |

**适用对象**：需要批量处理固定版式票据（如发票、收据、快递单、银行回单）的开发者或数据工程师。

**不适用对象**：需要理解文档语义、处理任意版式或手写内容的场景，请改用通用文档理解类工具。

---

## 二、触发方式与场景映射

当你的需求符合以下任一描述时，可激活本 Skill：

| 大白话场景 | 触发词建议 | 说明 |
|-----------|-----------|------|
| "帮我从一堆发票里把金额和税号抠出来" | 票据识别、字段抽取 | 批量结构化提取 |
| "这个模板的识别结果总是不准，能不能手动框一下位置" | OCR模板、mask矫正 | 模板定制与修正 |
| "识别出来的日期格式乱七八糟，帮我统一一下" | 票据后处理 | 结果规范化 |
| "我要做一个自定义的识别模板，支持拖拽框选" | 可视化模板 | 模板设计 |

---

## 三、标准执行流程

### 3.1 前置条件

| 项目 | 要求 |
|------|------|
| 文件命名 | 同一批次文件命名需遵循统一规则，如 `batch_001.png`、`batch_002.png` |
| 文件目录 | 所有待处理文件置于同一目录，避免路径含空格或中文 |
| 模板文件 | 若已有模板，需确认模板版本与当前票据版式一致 |
| 环境检查 | 运行 `--selftest` 确认依赖完整、OCR 引擎可用 |

### 3.2 执行步骤

**Step 1 — 准备输入**

将待处理文件放入工作目录，确认命名规范一致。若为 URL 输入，需确认链接可公开访问且无防盗链限制。

**Step 2 — 单样本试运行**

选取一个代表性样本执行模板匹配与字段抽取，核对输出字段与格式是否符合预期。此步骤用于验证模板有效性，避免批量执行时大面积出错。

```bash
# 示例：单文件处理
commonocrextractor --input ./samples/batch_001.png --template ./templates/invoice_v2.json --output ./results/
```

**Step 3 — 批量执行**

单样本验证通过后，对全量数据执行处理。建议保留原始文件备份，避免误覆盖。

```bash
# 示例：批量处理
commonocrextractor --input ./samples/ --template ./templates/invoice_v2.json --output ./results/ --batch
```

**Step 4 — 结果校验**

抽查输出条目，核对关键字段（如金额、日期、编号）与源数据一致性。若发现系统性偏差，返回 Step 2 调整模板或后处理规则。

### 3.3 输出规范

输出为 JSON 格式，结构如下：

```json
{
  "file": "batch_001.png",
  "fields": [
    {
      "name": "invoice_no",
      "value": "INV-2024-00123",
      "confidence": 0.98,
      "bbox": [120, 45, 320, 75]
    },
    {
      "name": "amount",
      "value": "¥12,500.00",
      "confidence": 0.95,
      "bbox": [420, 180, 580, 210]
    }
  ],
  "processing_time_ms": 356
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `file` | string | 源文件名 |
| `fields[].name` | string | 字段标识符，与模板定义一致 |
| `fields[].value` | string | 抽取的原始文本值 |
| `fields[].confidence` | float | 置信度，范围 0~1 |
| `fields[].bbox` | array | 坐标框 [x1, y1, x2, y2]，像素单位 |

---

## 四、置信度门控机制

当以下情况发生时，输出中对应字段值替换为 `[需核实:字段名]` 占位符，不进行猜测性填充：

| 触发条件 | 处理方式 |
|----------|----------|
| 置信度低于 0.60 | 字段值置为 `[需核实:字段名]` |
| OCR 结果为空但模板标记为必填 | 字段值置为 `[需核实:字段名]` |
| 字段值格式校验失败（如日期格式非法） | 字段值置为 `[需核实:字段名]`，并在 `warnings` 中注明原因 |
| mask 区域矫正后仍无法对齐 | 字段值置为 `[需核实:字段名]`，并输出矫正失败日志 |

**示例输出（含占位符）：**

```json
{
  "file": "batch_007.png",
  "fields": [
    {
      "name": "invoice_no",
      "value": "[需核实:invoice_no]",
      "confidence": 0.42,
      "bbox": [120, 45, 320, 75]
    }
  ],
  "warnings": ["invoice_no 置信度过低，OCR 文本模糊"]
}
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件不存在或路径错误 | "未找到指定文件，请检查路径" | 确认文件路径正确，文件名无拼写错误 |
| `E002` | 模板文件格式非法 | "模板 JSON 解析失败，请检查格式" | 使用 `--selftest` 验证模板结构，确认字段定义完整 |
| `E003` | OCR 引擎初始化失败 | "OCR 引擎加载失败，请检查依赖" | 重新安装依赖，确认 tesseract 或其他引擎可用 |
| `E004` | 图片解码失败 | "图片无法解码，请确认格式支持" | 转换图片格式为 PNG/JPG 后重试 |
| `E005` | mask 矫正区域越界 | "矫正区域超出图片边界" | 检查模板中 mask 坐标，确保在图片尺寸范围内 |
| `E006` | 批量处理中断 | "批量处理在第 N 个文件中断" | 查看日志定位失败文件，单独处理后合并结果 |

---

## 六、FAQ 与反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 模板不匹配导致全批失败 | 直接对全量数据执行，不做单样本验证 | 先跑单样本，确认字段对齐后再批量 |
| 置信度阈值设置过高 | 阈值设为 0.99，导致大量字段被置为占位符 | 根据实际场景调整阈值，建议 0.60~0.85 区间 |
| 忽略 mask 矫正 | 模板框选不准但直接使用，导致字段错位 | 使用 mask 矫正功能手动调整区域，再执行抽取 |
| 后处理规则过度定制 | 编写只适用于单一样本的硬编码规则 | 设计通用规则，覆盖同类型票据的常见变体 |
| 不保留原始备份 | 批量处理直接覆盖原文件 | 输出到独立目录，保留原始文件 |

---

## 七、渐进式阅读路径

### 新手路径（首次使用）

1. 阅读「能力边界速查卡」确认工具是否匹配需求
2. 查看「触发方式与场景映射」定位自己的使用场景
3. 按「标准执行流程」的 Step 1→2→3 顺序操作
4. 遇到异常时查阅「错误码体系」定位问题

### 进阶路径（深度定制）

1. 熟悉「输出规范」中的 JSON 结构，理解字段含义
2. 研究「置信度门控机制」，根据业务需求调整阈值
3. 设计自定义后处理规则，处理特殊格式（如日期、金额单位）
4. 使用 mask 矫正功能优化模板在复杂背景下的识别精度
5. 结合批量处理日志，建立针对特定票据类型的调优流程

---

## 八、参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | string | 必填 | 输入文件或目录路径 |
| `--template` | string | 必填 | 模板 JSON 文件路径 |
| `--output` | string | `./output/` | 输出目录 |
| `--batch` | bool | false | 批量处理模式 |
| `--confidence-threshold` | float | 0.60 | 置信度阈值，低于此值置为占位符 |
| `--mask-correction` | bool | false | 启用 mask 矫正 |
| `--selftest` | bool | false | 运行自检，验证环境与依赖 |
| `--version` | bool | false | 显示版本号 |

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因使用本 Skill 产生的任何直接或间接损失，包括但不限于数据丢失、业务中断、法律纠纷，本 Skill 作者及发布方不承担任何责任。
2. **禁止反向工程**：使用者不得对本 Skill 的底层实现进行反向工程、反编译、破解或试图提取源代码（法律允许的除外）。
3. **合规使用**：使用者需确保使用本 Skill 处理的数据来源合法，不侵犯第三方权益，不违反适用法律法规。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

<!-- user-agreement-injected -->

---

## 许可证（License）

本 Skill 采用 MIT 许可证授权：

```
MIT License

Copyright (c) 2024 原创作者（自持版权）

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

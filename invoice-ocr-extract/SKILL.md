---
slug: invoice-ocr-extract
name: invoice-ocr-extract
displayName: 票据识别 字段提取 结构化输出
description: 从发票图片或PDF中提取关键字段，输出结构化表格，支持批量处理与置信度标注。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 独立技能工坊
agent_created: true
trigger_words: ["invoice-ocr-extract", "发票识别", "发票提取", "OCR发票", "发票结构化", "票据解析", "发票字段抽取"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# 票据字段抽取与结构化输出指南

## 一、能力边界速查卡

| 维度 | 说明 |
|------|------|
| **核心能力** | 从发票图片或PDF中识别并提取关键字段（发票号码、开票日期、购买方信息、销售方信息、金额、税额、价税合计等），输出为结构化表格 |
| **支持格式** | JPG、PNG、PDF（单页或多页） |
| **批量处理** | 支持同一目录下多文件批量处理，自动生成汇总结果 |
| **置信度标注** | 每个字段附带识别置信度（高/中/低），低置信度字段自动标记 |
| **失败追踪** | 无法识别的文件单独记录失败原因，不中断整体流程 |

### 能做与不能做

**能做：**
- 标准版式发票（增值税普通发票、增值税专用发票）的字段提取
- 同一目录下批量处理，输出统一格式的表格
- 对识别结果进行置信度分级标注
- 生成失败明细清单，便于人工复核

**不能做：**
- 手写发票的准确识别（仅支持印刷体）
- 非发票类票据（如收据、行程单）的通用解析
- 对模糊、倾斜、反光严重的图片进行修复后再识别
- 自动验证发票真伪（需对接税务系统）

### 适用对象

- 财务人员：需要将纸质或电子发票信息录入系统
- 行政人员：处理报销单据时的信息登记
- 数据分析师：从大量发票中提取结构化数据用于分析

---

## 二、触发方式与场景映射

| 触发词/短语 | 适用场景 |
|-------------|----------|
| "发票识别" | 用户提供发票图片，希望提取关键信息 |
| "发票提取" | 用户需要从发票中获取特定字段（如税号、金额） |
| "OCR发票" | 用户明确要求使用OCR技术处理发票 |
| "发票结构化" | 用户希望将非结构化的发票信息转为表格 |
| "票据解析" | 用户手头有票据文件，需要自动解析内容 |
| "发票字段抽取" | 用户需要批量获取发票中的指定字段 |

---

## 三、标准操作流程

### 前置条件

1. 待处理文件已放入同一目录（建议目录路径不含中文和空格）
2. 文件命名规范一致（如：`invoice_001.jpg`、`invoice_002.pdf`）
3. 确认文件格式为支持的格式（JPG/PNG/PDF）
4. 确认文件清晰度：文字可辨认、无严重遮挡

### 执行步骤

**第一步：环境准备**

```bash
# 检查工具版本
invoice-ocr-extract --version

# 运行自检，确认环境正常
invoice-ocr-extract --selftest
```

**第二步：单样本试运行**

```bash
# 对单个文件执行提取
invoice-ocr-extract ./samples/invoice_001.jpg
```

检查输出结果：
- 关键字段是否完整（发票号码、金额、日期等）
- 字段值是否与源文件一致
- 置信度标注是否合理

**第三步：批量执行**

```bash
# 对目录下所有文件执行提取
invoice-ocr-extract ./invoices/
```

批量执行时自动完成：
- 遍历目录下所有支持格式的文件
- 逐个提取字段并汇总
- 生成结果文件（CSV格式）和失败清单

**第四步：结果校验**

- 抽查至少10%的条目，核对关键字段与源数据一致性
- 对低置信度字段进行人工复核
- 确认失败清单中的文件是否需要重新处理

### 输出规范

| 字段名 | 说明 | 示例 |
|--------|------|------|
| `file_name` | 源文件名 | invoice_001.jpg |
| `invoice_no` | 发票号码 | 12345678 |
| `invoice_date` | 开票日期 | 2024-03-15 |
| `buyer_name` | 购买方名称 | 某某科技有限公司 |
| `buyer_tax_id` | 购买方税号 | 91110108MA01XXXXX |
| `seller_name` | 销售方名称 | 某某商贸有限公司 |
| `seller_tax_id` | 销售方税号 | 91110105MA02XXXXX |
| `amount` | 金额（不含税） | 1000.00 |
| `tax` | 税额 | 130.00 |
| `total` | 价税合计 | 1130.00 |
| `confidence` | 整体置信度 | 高/中/低 |

---

## 四、置信度门控机制

当识别结果存在不确定性时，遵循以下规则：

| 情况 | 处理方式 |
|------|----------|
| 字段模糊无法辨认 | 输出 `[需核实:字段名]` 占位符 |
| 字段值超出合理范围 | 标记为低置信度，并附注说明 |
| 关键字段缺失 | 在失败清单中记录，不强行填充 |
| 多页PDF中某页无法识别 | 该页字段标记为 `[需核实:页码+字段名]` |

**原则：宁缺毋滥**——不编造任何字段值，所有不确定内容必须显式标注。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件格式不支持 | "文件格式不支持，请使用JPG/PNG/PDF格式" | 转换文件格式后重试 |
| `E002` | 文件无法读取 | "文件已损坏或权限不足，无法读取" | 检查文件完整性，确认读取权限 |
| `E003` | 未检测到发票 | "未在图片中检测到发票版式" | 确认图片内容为发票，调整拍摄角度 |
| `E004` | 关键字段缺失 | "发票号码和金额字段未能识别" | 检查图片清晰度，重新扫描 |
| `E005` | 批量处理中断 | "批量处理在第N个文件处中断" | 查看失败清单，单独处理失败文件 |
| `E006` | 置信度过低 | "整体置信度低于阈值，建议人工复核" | 人工核对源文件，手动录入 |

---

## 六、常见问题与反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 图片模糊导致识别率低 | 直接批量处理所有文件 | 先试运行单样本，确认质量后再批量 |
| 文件名混乱 | 依赖文件名排序结果 | 统一命名规范后再处理 |
| 发票版式特殊 | 期望所有发票都能完美识别 | 接受置信度标注，对低置信度字段人工复核 |
| 批量处理失败 | 忽略失败清单直接使用结果 | 检查失败清单，单独处理失败文件 |
| 结果未备份 | 直接覆盖原始文件 | 保留原始文件备份，结果另存新文件 |

---

## 七、分层次阅读路径

### 新手快速上手（5分钟）

1. 阅读「能力边界速查卡」了解工具能做什么
2. 按照「标准操作流程」的步骤执行一次单样本试运行
3. 查看输出结果，确认字段提取是否满足需求

### 进阶使用（15分钟）

1. 熟悉「置信度门控机制」，理解字段标注规则
2. 掌握「错误码体系」，能够独立排查常见问题
3. 阅读「常见问题与反模式对照」，避免典型错误

### 深度定制（30分钟+）

1. 根据业务需求调整输出字段配置
2. 自定义置信度阈值和校验规则
3. 集成到现有工作流中，实现自动化处理

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因使用本 Skill 产生的任何直接或间接损失，作者不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码。
3. **合法使用**：使用者应确保使用本 Skill 的行为符合当地法律法规，不得用于任何非法目的。
4. **数据安全**：使用者应自行负责处理数据的安全性和隐私保护。
5. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 许可证（License）

本 Skill 采用 MIT 许可证发布。

### MIT 许可证全文

```
MIT License

Copyright (c) 2024 独立技能工坊

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档，并根据实际场景进行验证。*

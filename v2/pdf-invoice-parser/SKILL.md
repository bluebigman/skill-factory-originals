---
slug: pdf-invoice-parser
name: pdf-invoice-parser
displayName: 发票解析 字段提取 一致性校验
description: 从PDF发票中提取结构化字段并校验数据一致性。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据工坊
agent_created: true
trigger_words: ["pdf-invoice-parser", "发票解析", "提取发票信息", "PDF发票转数据", "invoice extraction", "票据识别", "发票结构化"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# PDF 发票解析与校验 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输出示例 |
|--------|------|----------|
| 字段提取 | 从 PDF 发票中识别并提取关键业务字段 | 发票号码、开票日期、购销方信息、金额明细 |
| 结构化输出 | 将非结构化 PDF 内容转为 JSON/CSV 格式 | `{"invoice_no": "12345678"}` |
| 一致性校验 | 比对同一发票内多个字段的逻辑关系 | 价税合计 = 不含税金额 + 税额 |
| 批量处理 | 对同一目录下多份 PDF 文件执行相同流程 | 输出汇总表 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 手写发票识别 | 仅支持印刷体/电子发票 PDF，不支持手写内容识别 |
| 模糊图像修复 | 扫描件质量过低（分辨率 < 150dpi）时无法保证提取准确率 |
| 跨文件关联 | 不自动关联同一交易的多张发票（如红字发票与蓝字发票配对） |
| 格式转换 | 不提供 PDF 转 Word/Excel 的功能，仅输出结构化数据文件 |

### 1.3 适用对象

- **输入**：单页或多页 PDF 文件，文件大小 ≤ 20MB，页数 ≤ 10 页
- **输出**：JSON 文件（单份）或 CSV 汇总表（批量）
- **运行环境**：Python 3.8+，需安装 `pdfplumber`、`pandas` 库

---

## 二、触发方式与场景映射

### 2.1 触发词速查

| 触发词 | 适用场景 |
|--------|----------|
| `pdf-invoice-parser` | 直接调用 Skill 主命令 |
| `发票解析` | 中文场景下提取发票字段 |
| `提取发票信息` | 需要从 PDF 中获取结构化数据 |
| `PDF发票转数据` | 强调输出格式为数据文件 |
| `invoice extraction` | 英文场景触发 |
| `票据识别` | 泛指各类票据的字段提取 |
| `发票结构化` | 强调输出为结构化格式 |

### 2.2 场景映射表

| 用户说（大白话） | Skill 实际执行 |
|------------------|----------------|
| "帮我把这张发票的信息弄出来" | 提取单份 PDF 发票的全部字段，输出 JSON |
| "这堆发票文件帮我整理成表格" | 批量解析目录下所有 PDF，输出 CSV 汇总 |
| "看看发票上的金额对不对" | 执行字段一致性校验，输出校验报告 |
| "这个 PDF 是发票吗" | 检测文件类型，输出是否为发票及置信度 |

---

## 三、标准执行流程

### 3.1 前置条件

| 检查项 | 要求 | 验证方法 |
|--------|------|----------|
| 文件格式 | 必须是 PDF，且非加密 | 尝试打开文件，确认无密码保护 |
| 文件命名 | 建议格式：`发票_日期_编号.pdf` | 目视检查文件名 |
| 目录结构 | 待处理文件与输出目录分离 | 创建 `input/` 与 `output/` 两个目录 |
| 环境依赖 | Python 库已安装 | 运行 `pip list \| grep pdfplumber` |

### 3.2 执行步骤（分步编号）

**Step 1：准备输入**

```bash
mkdir -p input output
cp /path/to/your/invoices/*.pdf input/
```

**Step 2：单样本试运行**

```bash
python -m pdf_invoice_parser --input input/sample.pdf --output output/sample.json
```

检查 `output/sample.json` 中的字段是否完整、格式是否符合预期。

**Step 3：批量执行**

```bash
python -m pdf_invoice_parser --input input/ --output output/ --batch
```

批量模式下自动遍历 `input/` 目录下所有 `.pdf` 文件。

**Step 4：结果校验**

```bash
python -m pdf_invoice_parser --validate output/sample.json
```

校验规则包括：
- 发票号码格式（8-10位数字）
- 开票日期合法性（非未来日期）
- 金额逻辑（价税合计 = 不含税金额 × (1 + 税率)）

### 3.3 输出规范

**单份输出（JSON）**

```json
{
  "invoice_no": "12345678",
  "invoice_date": "2024-03-15",
  "seller_name": "某某科技有限公司",
  "seller_tax_id": "91110000XXXXXXXXXX",
  "buyer_name": "某某贸易有限公司",
  "buyer_tax_id": "91110000YYYYYYYYYY",
  "amount_without_tax": 1000.00,
  "tax_rate": 0.13,
  "tax_amount": 130.00,
  "amount_with_tax": 1130.00,
  "items": [
    {"name": "技术服务费", "quantity": 1, "unit_price": 1000.00}
  ],
  "validation": {
    "status": "pass",
    "checks": [
      {"rule": "amount_consistency", "result": "pass"},
      {"rule": "date_validity", "result": "pass"}
    ]
  }
}
```

**批量输出（CSV）**

| invoice_no | invoice_date | seller_name | amount_with_tax | validation_status |
|------------|--------------|-------------|-----------------|-------------------|
| 12345678 | 2024-03-15 | 某某科技 | 1130.00 | pass |
| 87654321 | 2024-03-16 | 某某商贸 | 2260.00 | fail |

---

## 四、置信度门控机制

### 4.1 字段置信度分级

| 置信度等级 | 判定标准 | 输出处理 |
|------------|----------|----------|
| 高（≥95%） | 字段清晰、格式标准、无歧义 | 直接输出实际值 |
| 中（80%-94%） | 字段存在但格式略有偏差 | 输出实际值并附加 `confidence` 字段 |
| 低（<80%） | 字段模糊、缺失或冲突 | 输出 `[需核实:字段名]` 占位符 |

### 4.2 占位符使用规则

当出现以下情况时，必须使用 `[需核实:字段名]` 占位：

```json
{
  "invoice_no": "[需核实:invoice_no]",
  "invoice_date": "2024-03-15",
  "amount_with_tax": "[需核实:amount_with_tax]"
}
```

**禁止行为**：
- 不得根据其他字段推算缺失字段的值
- 不得用相似发票的字段值填充
- 不得将占位符替换为 `null` 或空字符串

### 4.3 人工复核建议

当输出结果中占位符数量超过总字段数的 20% 时，建议：
1. 检查原始 PDF 质量（是否清晰、有无遮挡）
2. 尝试重新扫描或获取更高分辨率版本
3. 手动核对后补充字段值

---

## 五、错误码体系

### 5.1 错误码速查表

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件不存在 | "未找到指定文件，请检查路径" | 确认文件路径是否正确，文件是否已放入 `input/` 目录 |
| `E002` | 文件格式错误 | "文件不是有效的 PDF 格式" | 确认文件扩展名为 `.pdf`，尝试用其他 PDF 阅读器打开验证 |
| `E003` | 文件加密 | "PDF 文件已加密，无法解析" | 使用密码解密文件后重新执行 |
| `E004` | 解析超时 | "文件过大或页数过多，解析超时" | 拆分文件为单页 PDF，或压缩文件大小 |
| `E005` | 字段提取失败 | "关键字段提取失败，请检查发票版式" | 确认发票为常见版式，尝试调整扫描分辨率 |
| `E006` | 校验不通过 | "字段一致性校验未通过" | 查看校验报告，定位具体不一致的字段 |

### 5.2 错误处理流程

```
遇到错误
  ↓
记录错误码和上下文信息
  ↓
根据错误码查找对应修正步骤
  ↓
修正后重新执行
  ↓
连续失败 3 次 → 停止并人工介入
```

---

## 六、FAQ 与反模式对照

### 6.1 常见坑与反模式

| 反模式（错误做法） | 正确做法 | 原因说明 |
|-------------------|----------|----------|
| 直接批量处理所有文件，不做试运行 | 先用单个样本验证输出格式 | 避免批量输出格式错误导致返工 |
| 忽略校验结果，直接使用提取数据 | 抽查 10% 输出条目与源文件比对 | 校验能发现提取错误，减少下游数据污染 |
| 对模糊字段自行猜测补全 | 使用 `[需核实:字段]` 占位符 | 猜测值会污染数据，占位符提示人工介入 |
| 修改原始 PDF 文件 | 保留原始文件备份，输出到独立目录 | 原始文件是唯一事实来源，不可变更 |
| 依赖单一字段判断发票真伪 | 综合多个字段交叉验证 | 单一字段可能被伪造或误识别 |

### 6.2 典型问题解答

**Q1：发票扫描件模糊怎么办？**
A：建议重新扫描，分辨率不低于 300dpi。若无法改善，可接受部分字段为 `[需核实]` 状态，人工补充。

**Q2：批量处理时个别文件失败，是否影响整体？**
A：不影响。失败文件会记录错误码并跳过，其余文件正常处理。处理完成后查看错误报告即可。

**Q3：如何处理多页发票？**
A：默认解析所有页并合并字段。若字段跨页分布，会优先取第一页出现的值，并在输出中标注 `page` 字段。

---

## 七、渐进式披露指南

### 7.1 速查卡（30 秒上手）

1. 把 PDF 放入 `input/` 目录
2. 运行 `python -m pdf_invoice_parser --input input/ --output output/ --batch`
3. 打开 `output/` 下的 JSON 或 CSV 文件查看结果
4. 检查 `validation.status` 是否为 `pass`

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」了解工具限制
2. 按「标准执行流程」Step 1-2 完成单样本测试
3. 确认输出格式符合预期后，再执行批量处理
4. 遇到问题查阅「错误码体系」

### 7.3 进阶路径（深度使用）

1. 自定义校验规则：修改 `config/validation_rules.json` 添加业务规则
2. 扩展字段映射：编辑 `config/field_mapping.yaml` 适配特殊发票版式
3. 集成到自动化流程：通过 CLI 参数 `--format json` 输出机器可读结果
4. 性能调优：对超大文件使用 `--pages 1-3` 参数限定解析范围

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用条款**

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因使用本 Skill 产生的任何直接或间接损失，包括但不限于数据错误、业务中断、法律风险，均由使用者自行承担。

2. **数据安全**：使用者应确保待处理数据不包含违反法律法规的内容。本 Skill 不承担数据泄露或不当使用的责任。

3. **禁止反向工程**：使用者不得对本 Skill 进行反向工程、反编译、破解或试图获取源代码逻辑。

4. **合规使用**：使用者应遵守所在国家/地区关于发票处理、数据保护的相关法律法规。

5. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 数据工坊

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证适用性。*

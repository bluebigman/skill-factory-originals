---
slug: pdf-invoice-parser
name: pdf-invoice-parser
displayName: 发票解析 字段提取 一致性校验
description: 从PDF发票中提取结构化字段并校验数据一致性。
version: 1.0.0
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/pdf-invoice-parser
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 独立技能工坊
agent_created: true
trigger_words: ["pdf发票解析", "发票信息提取", "invoice-parser", "发票字段校验", "票据数据抽取"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# PDF 发票解析与一致性校验 Skill 文档

## 一、能力边界（一页纸速查卡）

本 Skill 面向**需要从 PDF 格式发票中批量提取关键字段，并验证提取结果内部逻辑一致性**的场景。适用于财务人员、数据分析师、自动化流程开发者。

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 字段提取 | 从 PDF 发票中识别并抽取结构化字段 | 发票号码、开票日期、购买方名称、销售方名称、金额（不含税）、税额、价税合计 |
| 一致性校验 | 对提取出的字段进行逻辑关系验证 | 价税合计 = 金额 + 税额；发票号码格式合法；日期格式合法且不晚于当前日期 |
| 格式确认 | 检查输入 PDF 是否为有效文件、是否可解析 | 文件扩展名、文件头魔数、页数检查 |
| 错误反馈 | 输入不符合预期时，返回明确的错误说明与正确格式示例 | 见「错误码体系」章节 |

### 1.2 不能做什么（明确边界）

| 限制项 | 说明 |
|--------|------|
| 不处理扫描件 OCR | 本 Skill 仅处理**文本型 PDF**（即由电子发票系统直接生成的 PDF）。若 PDF 为扫描图片，需先经过 OCR 预处理，本 Skill 不承担 OCR 功能。 |
| 不识别手写内容 | 仅识别标准印刷体文本。 |
| 不保证 100% 识别率 | 受限于 PDF 内部编码方式（如某些非标准字体映射），个别字段可能无法提取。此时将输出 `[需核实:字段名]` 占位符。 |
| 不进行税务合规判断 | 本 Skill 只做字段提取与逻辑一致性校验，**不判断发票真伪**（如是否在税务局系统中存在）、不判断业务合规性。 |
| 不处理加密 PDF | 若 PDF 设置了打开密码，无法解析。 |

### 1.3 适用对象

- **输入**：单个 PDF 文件路径（本地文件或可访问的 URL）。
- **输出**：JSON 格式的结构化字段集合 + 校验报告。
- **不适用**：批量文件夹处理（需外部循环调用）、非 PDF 格式（如图片、Word）。

---

## 二、触发方式

当用户输入包含以下任一关键词或意图时，本 Skill 被激活：

| 触发词（trigger_words） | 用户可能说的大白话 | 映射场景 |
|--------------------------|-------------------|----------|
| pdf发票解析 | "帮我看看这张发票上写了啥" | 提取发票所有关键字段 |
| 发票信息提取 | "把这个 PDF 里的发票号、金额弄出来" | 提取指定字段 |
| invoice-parser | "Parse this invoice PDF" | 英文场景下的提取请求 |
| 发票字段校验 | "帮我核对一下这张发票的金额对不对" | 提取 + 一致性校验 |
| 票据数据抽取 | "把这张票的数据结构化存到表格里" | 提取并输出 JSON 供下游使用 |

**触发后的默认行为**：若用户仅提供文件路径，默认执行「完整提取 + 一致性校验」；若用户指定了字段列表，则仅提取指定字段并校验这些字段间的逻辑关系。

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 文件存在 | 文件路径有效，且文件大小 > 0 字节 | 文件系统访问 |
| 文件类型 | 扩展名为 `.pdf`，且文件头为 `%PDF-` | 读取前 5 字节 |
| 文件可读 | 未加密、无打开密码 | 尝试打开并读取首页文本 |
| 文本可提取 | 首页包含至少 10 个可识别字符 | 提取首页文本并统计长度 |

若以上任一条件不满足，直接跳转至「错误码体系」章节返回对应错误。

### 3.2 执行步骤（分步编号）

**步骤 1：收集用户输入并确认格式**

- 接收参数：`file_path`（必填，字符串）、`fields`（可选，字符串数组，指定要提取的字段名）。
- 确认 `file_path` 格式：必须为合法的文件路径或 URL 字符串，长度 ≤ 2048 字符。
- 确认 `fields` 格式：若提供，必须是数组，且每个元素为字符串，且元素必须在「可提取字段清单」内（见下表）。

**可提取字段清单（字段名大小写不敏感，输出统一为小写）**：

| 字段名 | 说明 | 示例值 |
|--------|------|--------|
| invoice_no | 发票号码 | `"12345678"` |
| invoice_date | 开票日期（YYYY-MM-DD） | `"2025-06-15"` |
| buyer_name | 购买方名称 | `"某某科技有限公司"` |
| seller_name | 销售方名称 | `"某某商贸有限公司"` |
| amount_excl_tax | 金额（不含税，数字，单位元） | `1000.00` |
| tax_amount | 税额（数字，单位元） | `130.00` |
| total_amount | 价税合计（数字，单位元） | `1130.00` |

**步骤 2：按功能逻辑处理输入内容**

- 打开 PDF 文件，逐页提取文本内容。
- 使用正则表达式模式匹配各字段。匹配规则示例：
  - `invoice_no`：匹配 `发票号码[:：]\s*([0-9]{8,20})`
  - `invoice_date`：匹配 `开票日期[:：]\s*(\d{4}年\d{2}月\d{2}日)` 并转换为 `YYYY-MM-DD`
  - `total_amount`：匹配 `价税合计[（(]小写[)）]?[:：]\s*[¥￥]?\s*([0-9]+\.[0-9]{2})`
- 若某字段匹配失败，则标记为 `[需核实:字段名]`，不中断流程。

**步骤 3：生成结果并校验完整性**

- 组装 JSON 结果对象，结构如下：

```json
{
  "file_path": "path/to/invoice.pdf",
  "extracted_fields": {
    "invoice_no": "12345678",
    "invoice_date": "2025-06-15",
    "buyer_name": "某某科技有限公司",
    "seller_name": "某某商贸有限公司",
    "amount_excl_tax": 1000.00,
    "tax_amount": 130.00,
    "total_amount": 1130.00
  },
  "validation_report": {
    "passed": true,
    "checks": [
      {"rule": "total_equals_sum", "passed": true, "detail": "1130.00 = 1000.00 + 130.00"},
      {"rule": "date_format", "passed": true, "detail": "2025-06-15 符合 YYYY-MM-DD"},
      {"rule": "invoice_no_format", "passed": true, "detail": "8位数字"}
    ]
  },
  "warnings": []
}
```

- 校验规则（内置 4 项）：

| 规则 ID | 规则描述 | 判定条件 |
|---------|----------|----------|
| `total_equals_sum` | 价税合计 = 金额 + 税额 | `abs(total - (amount + tax)) < 0.01` |
| `date_format` | 日期格式合法 | 匹配 `YYYY-MM-DD` 且为真实存在的日期 |
| `date_not_future` | 开票日期不晚于当前日期 | `invoice_date <= today` |
| `invoice_no_format` | 发票号码为 8-20 位数字 | 正则 `^[0-9]{8,20}$` |

- 若任一校验失败，`passed` 置为 `false`，并在 `checks` 中标注失败项。

### 3.3 输出规范

- **成功**：返回上述 JSON 对象，HTTP 状态码 200（若为 API 调用）。
- **部分成功**：存在 `[需核实:字段]` 占位符，`passed` 可能为 `true`（若占位字段不参与校验）或 `false`（若占位字段参与校验且无法确认）。`warnings` 数组会列出所有占位字段。
- **失败**：返回错误码 + 错误信息 + 正确格式示例（见下节）。

---

## 四、置信度门控

本 Skill 遵循「不编造」原则。在以下情况，输出 `[需核实:字段名]` 占位符，而非猜测值：

| 场景 | 处理方式 |
|------|----------|
| 正则匹配失败 | 该字段输出 `[需核实:字段名]` |
| 匹配到多个候选值（如页面出现多个金额） | 全部候选值放入 `warnings`，字段输出 `[需核实:字段名]` |
| 金额字段解析为非数字字符 | 输出 `[需核实:字段名]` |
| 日期字段解析为 `2025-13-45` 等非法日期 | 输出 `[需核实:字段名]`，并在 `warnings` 中注明原始文本 |

**禁止行为**：不得根据其他字段反推缺失字段的值（例如：不得用 `total - tax` 反推 `amount`）。所有字段必须独立提取。

---

## 五、错误码体系

| 错误码 | 含义 | 用户提示话术 | 修正步骤 |
|--------|------|--------------|----------|
| `E1001` | 文件不存在 | "未找到指定文件，请检查路径是否正确。" | 确认文件路径；若为 URL，确认链接可访问 |
| `E1002` | 文件类型错误 | "文件不是有效的 PDF 格式。正确格式：文件扩展名为 .pdf，且文件头为 %PDF-。" | 转换文件为 PDF 格式后重试 |
| `E1003` | 文件加密 | "PDF 文件已加密，无法解析。请先解除打开密码。" | 使用 PDF 解密工具去除密码 |
| `E1004` | 无可提取文本 | "PDF 中未检测到可提取的文本，可能为扫描件。本 Skill 不支持 OCR，请先对扫描件进行文字识别。" | 对 PDF 执行 OCR 后，将生成的文本型 PDF 传入 |
| `E1005` | 字段名不合法 | "请求的字段不在可提取清单内。合法字段：invoice_no, invoice_date, buyer_name, seller_name, amount_excl_tax, tax_amount, total_amount。" | 检查 `fields` 参数拼写 |
| `E1006` | 参数缺失 | "缺少必填参数 file_path。" | 补充文件路径参数 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式（错误做法） | 正模式（正确做法） |
|----|--------------------|--------------------|
| 扫描件当文本处理 | 直接传入扫描件，期望提取成功 | 先 OCR，再传入文本型 PDF |
| 金额精度丢失 | 将金额字段解析为浮点数后直接比较 | 使用 Decimal 类型或保留两位小数比较，容差 0.01 |
| 多页发票只读第一页 | 只提取第一页文本 | 遍历所有页，合并文本后再匹配 |
| 日期格式混乱 | 假设所有发票日期格式一致 | 支持 `YYYY年MM月DD日`、`YYYY-MM-DD`、`YYYY/MM/DD` 三种格式，统一输出 `YYYY-MM-DD` |
| 忽略校验失败 | 提取成功即返回，不执行校验 | 始终执行内置 4 项校验，并在报告中体现 |

### 6.2 反模式对照表

| 反模式描述 | 后果 | 建议替代方案 |
|------------|------|--------------|
| 用 `total - tax` 反推 `amount` | 若 `total` 或 `tax` 提取错误，`amount` 也会错误，且无法察觉 | 独立提取 `amount`，若缺失则输出 `[需核实:amount]` |
| 对加密 PDF 尝试暴力破解密码 | 违反安全规范，且大概率失败 | 直接返回 `E1003`，引导用户解密 |
| 将 `[需核实:字段]` 替换为 `null` 或空字符串 | 下游程序可能将空值当作有效值处理，造成数据错误 | 保留占位符，并在 `warnings` 中明确标注 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
输入：PDF 文件路径
输出：JSON（字段 + 校验报告）
必记规则：
  1. 只处理文本型 PDF，扫描件先 OCR
  2. 提取失败输出 [需核实:字段]，不猜测
  3. 内置校验：total = amount + tax
  4. 错误码 E1001~E1006 对应 6 种常见问题
```

### 7.2 分层次阅读路径

**新手路径（首次使用）**：

1. 阅读「一、能力边界」中的「能做什么」和「不能做什么」。
2. 阅读「三、标准流程」中的「步骤 1」了解输入参数。
3. 阅读「五、错误码体系」中的 `E1001` 和 `E1004`，这是最常见的两个错误。
4. 直接尝试一个样例 PDF，观察输出 JSON 结构。

**进阶路径（集成到自动化流程）**：

1. 完整阅读「三、标准流程」全部内容，理解校验规则。
2. 阅读「四、置信度门控」，设计下游对 `[需核实:字段]` 的处理逻辑。
3. 阅读「六、FAQ 反模式」，避免常见实现陷阱。
4. 自定义扩展：在「可提取字段清单」基础上增加新字段时，需同步更新「步骤 2」的正则匹配规则和「步骤 3」的校验规则。

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款**：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的提取结果与校验报告仅供参考，不构成任何形式的专业建议或保证。因依赖本 Skill 输出而导致的直接或间接损失，Skill 作者及发布者不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 的底层逻辑、提示词结构、内部参数进行反向工程、反编译、提取或复制，亦不得将其用于训练竞争性模型或生成类似工具。
3. **合法使用**：使用者须确保所处理的 PDF 发票来源合法，且使用场景符合当地法律法规。本 Skill 不用于伪造、变造或欺诈目的。
4. **无担保**：本 Skill 按「现状」提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性及不侵权保证。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2025 独立技能工坊

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

*文档版本：1.0.0 | 最后更新：2025-06-15 | 本 Skill 由 AI 辅助生成，仅供参考。*

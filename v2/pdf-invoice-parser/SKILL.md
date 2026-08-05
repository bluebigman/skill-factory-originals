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
trigger_words: ["pdf-invoice-parser", "发票解析", "提取发票信息", "PDF发票转数据", "invoice extraction", "票据识别", "发票数据化"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# PDF 发票解析与一致性校验 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入格式 | 单页或多页 PDF 发票文件 | 图片格式（JPG/PNG）需先转 PDF |
| 字段提取 | 发票代码、号码、开票日期、购买方/销售方名称与税号、金额（不含税/税额/价税合计）、备注 | 手写体发票、模糊扫描件 |
| 校验能力 | 价税合计 = 不含税金额 + 税额；发票号码与代码位数合法性；日期格式合法性 | 与税务系统实时联网核验真伪 |
| 输出格式 | 结构化 JSON / CSV / Markdown 表格 | 直接写入财务软件数据库 |
| 批量处理 | 同一目录下多文件顺序处理 | 跨目录递归扫描（需手动指定） |

### 1.2 适用对象

- 财务人员：需要将纸质或电子发票信息录入系统的场景
- 行政人员：报销单附件信息登记
- 开发者：需要将发票数据接入自建系统的场景

### 1.3 不适用场景

- 发票真伪核验（需对接税务官方接口）
- 非中文发票（如英文、日文发票）
- 超过 10MB 或超过 50 页的超大文件

---

## 二、触发方式与场景映射

### 2.1 触发词

直接使用以下任一说法即可唤起本 Skill：

| 触发词 | 使用场景 |
|--------|----------|
| `pdf-invoice-parser` | 命令行直接调用 |
| `发票解析` | 日常口语化表达 |
| `提取发票信息` | 明确表达提取需求 |
| `PDF发票转数据` | 强调格式转换 |
| `invoice extraction` | 英文场景 |
| `票据识别` | 泛指各类票据 |
| `发票数据化` | 强调数据落地 |

### 2.2 场景映射表

| 你说的话 | Skill 实际做的事 |
|----------|-----------------|
| "帮我把这张发票的信息弄出来" | 解析 PDF，输出结构化字段 |
| "这批发票要录入系统，先整理一下" | 批量解析并输出统一格式 |
| "看看这张发票金额对不对" | 提取字段并执行一致性校验 |
| "发票上的税号帮我核一下" | 提取税号字段并校验位数合法性 |

---

## 三、标准操作流程

### 3.1 前置条件

| 条件项 | 要求 |
|--------|------|
| 文件格式 | `.pdf` 后缀，非加密、非扫描图片型 |
| 文件命名 | 建议统一为 `发票_日期_序号.pdf`（如 `发票_20250115_001.pdf`） |
| 目录结构 | 所有待处理文件置于同一目录，避免嵌套子目录 |
| 环境依赖 | Python 3.9+，已安装 `pdfplumber` 与 `pandas` 库 |

### 3.2 执行步骤

**第一步：环境确认**

```bash
python -m pip install pdfplumber pandas
```

**第二步：单样本试运行**

```bash
pdf-invoice-parser --input ./sample_invoice.pdf --output ./result.json
```

检查输出 JSON 中以下字段是否完整：

```json
{
  "invoice_code": "发票代码",
  "invoice_number": "发票号码",
  "issue_date": "YYYY-MM-DD",
  "buyer_name": "购买方名称",
  "buyer_tax_id": "购买方税号",
  "seller_name": "销售方名称",
  "seller_tax_id": "销售方税号",
  "amount_excluding_tax": 0.00,
  "tax_amount": 0.00,
  "total_amount": 0.00,
  "remark": "备注"
}
```

**第三步：批量执行**

```bash
pdf-invoice-parser --input ./all_invoices/ --output ./output/ --batch
```

执行前确认：

- 原始 PDF 已备份至 `./backup/` 目录
- 输出目录存在且有写入权限

**第四步：结果抽查**

随机抽取 3-5 条输出记录，与源 PDF 人工比对以下关键字段：

- 发票号码（逐位核对）
- 价税合计金额（小数点后两位）
- 购买方税号（18 位统一社会信用代码）

### 3.3 输出规范

| 输出项 | 格式要求 |
|--------|----------|
| 金额字段 | 保留两位小数，如 `1234.50` |
| 日期字段 | `YYYY-MM-DD` 格式 |
| 税号字段 | 纯数字或字母数字组合，无空格 |
| 缺失字段 | 输出 `[需核实:字段名]` 占位符 |
| 文件编码 | UTF-8 无 BOM |

---

## 四、置信度门控机制

### 4.1 占位符规则

当以下情况出现时，**不得**编造数据，必须输出占位符：

| 情况 | 输出 |
|------|------|
| 字段在 PDF 中无法定位 | `[需核实:字段名]` |
| 金额数字模糊不清 | `[需核实:total_amount]` |
| 税号位数不足或超长 | `[需核实:buyer_tax_id]` |
| 日期格式异常 | `[需核实:issue_date]` |

### 4.2 校验失败处理

当一致性校验不通过时：

- 输出 `"validation_status": "FAILED"`
- 在 `"validation_errors"` 数组中列出具体差异
- 不自动修正数据，交由人工判断

### 4.3 置信度分级

| 级别 | 条件 | 处理方式 |
|------|------|----------|
| 高 | 所有字段提取成功且校验通过 | 正常输出 |
| 中 | 1-2 个非关键字段缺失 | 输出占位符，标注 `"confidence": "medium"` |
| 低 | 关键字段（金额/税号）缺失或校验失败 | 输出占位符，标注 `"confidence": "low"`，建议人工复核 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件不存在 | "未找到指定文件，请检查路径" | 确认文件路径是否正确，文件名是否含特殊字符 |
| `E002` | 文件格式错误 | "文件不是有效的 PDF 格式" | 确认文件后缀为 `.pdf`，尝试用阅读器打开验证 |
| `E003` | PDF 加密 | "PDF 已加密，无法解析" | 使用密码解密后重试 |
| `E004` | 扫描件无文本层 | "未检测到可提取的文本，疑似扫描件" | 先运行 OCR 工具生成文本层 |
| `E005` | 字段提取不完整 | "以下字段未能提取：[字段列表]" | 检查 PDF 是否为标准发票版式，或手动补充 |
| `E006` | 一致性校验失败 | "价税合计与分项金额不一致" | 人工核对原始发票，确认是否录入错误 |
| `E007` | 批量处理中断 | "第 N 个文件处理失败，已跳过" | 查看错误日志，单独处理失败文件 |

---

## 六、FAQ 与反模式对照

### 6.1 常见坑

| 坑 | 反模式（错误做法） | 正确做法 |
|----|-------------------|----------|
| 扫描件直接解析 | 拿手机拍照的 PDF 直接跑解析 | 先 OCR 识别，再执行解析 |
| 金额精度丢失 | 用浮点数直接存储金额 | 使用 Decimal 类型，保留两位小数 |
| 忽略备注字段 | 只提取金额和税号，不要备注 | 备注可能含合同号、项目名等关键信息 |
| 批量处理不备份 | 直接对原目录执行批量解析 | 先复制到工作目录，保留原始备份 |
| 校验失败仍入库 | 忽略 validation_status 直接入库 | 校验失败的数据必须人工确认后才能入库 |

### 6.2 反模式对照表

| 场景 | 反模式 | 推荐模式 |
|------|--------|----------|
| 发票号码提取 | 正则匹配 8 位数字就认为是号码 | 结合发票代码前缀和版式位置综合判断 |
| 日期提取 | 看到 2024 就认为是年份 | 校验月份 01-12、日期 01-31 的合法性 |
| 税号提取 | 提取 15 位或 18 位数字即通过 | 校验 18 位统一社会信用代码的校验位 |

---

## 七、渐进式学习路径

### 7.1 速查卡（30 秒上手）

```bash
# 单文件解析
pdf-invoice-parser --input invoice.pdf --output result.json

# 批量解析
pdf-invoice-parser --input ./folder/ --output ./out/ --batch

# 自检
pdf-invoice-parser --selftest
```

### 7.2 新手路径（首次使用）

1. 阅读本 Skill 的能力边界，确认适用场景
2. 准备一个标准 PDF 发票样本
3. 执行单样本试运行，核对输出字段
4. 确认无误后，再处理批量数据

### 7.3 进阶路径（深度使用）

1. 熟悉错误码体系，掌握常见问题的排查方法
2. 理解置信度门控机制，学会处理占位符数据
3. 自定义输出模板，对接业务系统
4. 对特殊版式发票（如电子发票、卷式发票）进行适配

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因使用本 Skill 产生的任何直接或间接损失，包括但不限于数据错误、业务中断、财务损失，本 Skill 作者不承担任何责任。

2. **数据准确性**：本 Skill 输出的数据仅供辅助参考，不构成对数据准确性的保证。关键财务数据必须经人工复核后方可正式使用。

3. **禁止反向工程**：使用者不得对本 Skill 进行反向工程、反编译、破解或试图获取其底层实现逻辑。

4. **合规使用**：使用者应确保使用本 Skill 的行为符合所在国家或地区的法律法规，不得用于任何非法用途。

5. **免责声明**：本 Skill 由 AI 辅助生成，仅供学习参考。作者不对其适用性、准确性、完整性作任何明示或暗示的保证。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2025 数据工坊

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

*文档版本：1.0.0 | 最后更新：2025 年 1 月*

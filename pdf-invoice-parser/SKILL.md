---
slug: pdf-invoice-parser
name: pdf-invoice-parser
displayName: 发票解析 字段提取 一致性校验
description: 从PDF发票中提取结构化字段并校验数据一致性。
version: 2.0.0
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

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


# PDF 发票解析与一致性校验

**一句话定位**：从 PDF 发票（中国增值税电子/专用/数电票）中提取结构化字段并校验数据一致性，为财务人员、行政人员和开发者提供开箱即用的发票数据化工具。

## 快速开始 Quick Start

| 场景 | 命令 | 预期结果 |
|------|------|----------|
| 解析单个 PDF 发票 | `python run.py invoice.pdf` | 输出 JSON 格式的发票结构化字段 |
| 批量解析目录下所有 PDF | `python run.py ./invoices/ --format csv` | 生成 CSV 文件，包含所有发票数据 |
| 自检功能 | `python run.py --selftest` | 运行内置测试用例，验证核心功能正常 |

## 适用场景 When to Use

**什么时候用：**
- 财务人员需要将纸质或电子发票信息录入系统
- 行政人员处理报销单附件信息登记
- 开发者需要将发票数据接入自建系统
- 需要批量处理多个 PDF 发票文件

**什么时候不要用：**
- 发票真伪核验（需对接税务官方接口）
- 非中文发票（如英文、日文发票）
- 超过 10MB 或超过 50 页的超大文件
- 手写体发票或模糊扫描件（无文本层）

## 能力总览 Capabilities

| 能力 | 命令/参数 | 示例 |
|------|-----------|------|
| 单文件解析 | `python run.py <file.pdf>` | `python run.py invoice.pdf` |
| 目录批量解析 | `python run.py <directory>` | `python run.py ./invoices/` |
| 远程 URL 解析 | `python run.py <http_url>` | `python run.py https://example.com/invoice.pdf` |
| 输出格式选择 | `--format {json,jsonl,csv}` | `python run.py invoice.pdf --format csv` |
| 输出文件指定 | `-o, --output <path>` | `python run.py invoice.pdf -o result.json` |
| 并发处理 | `--workers <num>` | `python run.py ./invoices/ --workers 8` |
| 网络重试 | `--retries <num>` | `python run.py https://... --retries 5` |
| 网络超时 | `--timeout <seconds>` | `python run.py https://... --timeout 60` |
| 详细日志 | `--verbose` | `python run.py invoice.pdf --verbose` |
| 自检模式 | `--selftest` | `python run.py --selftest` |

## 模块决策表 Decision Table

| 用户意图 | 模块/命令 | 读取指引 |
|----------|-----------|----------|
| 解析单个发票文件 | `python run.py <file.pdf>` | 查看「示例 Examples」中的单文件解析示例 |
| 批量处理多个发票 | `python run.py <directory>` | 查看「示例 Examples」中的批量解析示例 |
| 需要 CSV 格式输出 | `--format csv` | 查看「能力总览 Capabilities」中的格式参数 |
| 处理远程发票链接 | `python run.py <http_url>` | 查看「示例 Examples」中的远程 URL 解析示例 |
| 验证安装是否正常 | `--selftest` | 查看「安装与配置 Installation」中的自检说明 |

## 示例 Examples

### 示例 1：单文件解析（JSON 输出）

```bash
python run.py invoice.pdf
```

输出：
```json
{
  "file": "invoice.pdf",
  "code": "031001900111",
  "number": "12345678",
  "date": "2024-01-15",
  "kind": "增值税专用发票",
  "buyer": "示例科技有限公司",
  "buyer_tax": "91110108MA01XXXXX",
  "seller": "示例供应商有限公司",
  "seller_tax": "91110105MA02XXXXX",
  "amount": "1000.00",
  "tax": "130.00",
  "total": "1130.00",
  "total_cn": "壹仟壹佰叁拾元整",
  "rate": "13%",
  "items": [
    {"name": "技术服务费", "spec": "", "unit": "次", "qty": "1", "price": "1000.00", "amount": "1000.00"}
  ],
  "checks": {
    "amount_tax_total": true,
    "total_cn_match": true,
    "number_digits": true,
    "date_valid": true
  }
}
```

### 示例 2：批量解析（CSV 输出）

```bash
python run.py ./invoices/ --format csv -o result.csv
```

输出文件 `result.csv` 内容：
```csv
file,code,number,date,kind,buyer,buyer_tax,seller,seller_tax,amount,tax,total,total_cn,rate
invoice1.pdf,031001900111,12345678,2024-01-15,增值税专用发票,示例科技有限公司,91110108MA01XXXXX,示例供应商有限公司,91110105MA02XXXXX,1000.00,130.00,1130.00,壹仟壹佰叁拾元整,13%
invoice2.pdf,031001900112,87654321,2024-01-16,增值税普通发票,示例贸易有限公司,91110106MA03XXXXX,示例服务有限公司,91110107MA04XXXXX,500.00,65.00,565.00,伍佰陆拾伍元整,13%
```

### 示例 3：远程 URL 解析

```bash
python run.py https://example.com/invoice.pdf --timeout 60
```

输出与示例 1 相同的 JSON 格式结果。

## 安装与配置 Installation

### 环境要求

- Python 3.9+
- 操作系统：Windows / macOS / Linux

### 依赖安装

```bash
pip install pdfplumber pypdf
```

### 验证安装

```bash
python run.py --selftest
```

如果输出 `All selftests passed.` 则表示安装成功。

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `PDF_INVOICE_RETRIES` | 网络请求重试次数 | 3 |
| `PDF_INVOICE_TIMEOUT` | 网络请求超时（秒） | 30 |
| `PDF_INVOICE_WORKERS` | 批量处理最大并发数 | 4 |

## 常见问题 Troubleshooting

| 错误现象 | 原因 | 解决办法 |
|----------|------|----------|
| `[E001] 输入路径不存在或不可读` | 文件路径错误或权限不足 | 检查文件路径是否正确，确认有读取权限 |
| `[E002] 文件不是有效 PDF` | 文件格式错误或已损坏 | 确认文件是有效的 PDF 格式，尝试重新导出 |
| `[E003] PDF 已加密，需要口令` | PDF 文件设置了密码保护 | 使用解密工具去除密码保护 |
| `[E004] PDF 无文本层且 OCR 依赖未安装` | 扫描件 PDF 没有文本层 | 安装 OCR 工具（如 tesseract）或使用带文本层的 PDF |
| `[E005] 未安装任何 PDF 解析引擎` | 缺少 pdfplumber 或 pypdf | 运行 `pip install pdfplumber pypdf` |
| `[E006] 文本提取成功但未识别出发票关键字段` | PDF 格式特殊或非标准发票 | 检查 PDF 是否为标准增值税发票格式 |
| `[E007] 金额字段解析失败` | 金额格式异常 | 检查 PDF 中的金额格式是否为数字 |
| `[E008] 一致性校验未通过` | 发票数据存在不一致 | 检查发票各项金额是否计算正确 |
| `[E009] 批量目录未找到任何 PDF` | 目录中没有 PDF 文件 | 确认目录路径正确且包含 PDF 文件 |
| `[E010] 输出写入失败` | 输出路径无写入权限 | 检查输出路径权限，确认目录存在 |

## 最佳实践 Best Practices

### 使用建议

1. **批量处理时使用 CSV 格式**：CSV 格式便于导入 Excel 或财务软件
2. **网络请求设置合理超时**：处理远程 URL 时，建议设置 `--timeout 60` 以上
3. **使用 `--verbose` 查看详细日志**：排查问题时开启详细日志
4. **定期运行 `--selftest`**：确保环境配置正确

### 注意事项

- 本工具不提供发票真伪核验功能，如需核验请对接税务官方接口
- 对于扫描件 PDF，请先进行 OCR 处理
- 处理敏感发票数据时，注意数据安全

### 性能优化

- 批量处理时可通过 `--workers` 参数调整并发数
- 大文件处理时建议使用 `--format jsonl` 流式输出

## 相关资源 Related

- [pdfplumber 文档](https://github.com/jsvine/pdfplumber)
- [pypdf 文档](https://github.com/py-pdf/pypdf)
- [中国增值税发票格式规范](https://inv-veri.chinatax.gov.cn/)

---

## 许可证（License）

```text
MIT License

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
```

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。

> 本内容由 AI 生成，仅供学习参考
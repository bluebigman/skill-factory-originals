---
slug: invoice-ocr-extract
name: invoice-ocr-extract
displayName: 票据识别 字段抽取 结构化输出
description: 从发票图片或PDF中抽取关键字段，输出结构化表格，支持批量与置信度标注。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 知微技能工坊
agent_created: true
trigger_words: ["invoice-ocr-extract", "发票识别", "发票提取", "OCR发票", "发票结构化", "票据解析", "发票信息抽取"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 票据识别与字段抽取技能（invoice-ocr-extract）

## 一、能力边界速查卡

| 维度 | 说明 |
|------|------|
| **核心能力** | 从发票图片（JPG/PNG）或 PDF 文件中识别并抽取关键字段，输出为 CSV 或 JSON 结构化数据 |
| **支持字段** | 发票号码、开票日期、购买方名称、销售方名称、金额（不含税）、税额、价税合计、发票类型 |
| **批量处理** | 支持将同一目录下的多个发票文件一次性处理，输出合并表格 |
| **置信度标注** | 每个字段附带识别置信度分数（0~1），低于阈值的字段自动标记 |
| **不能做的事** | 不能验证发票真伪；不能处理手写发票；不能识别模糊或严重倾斜的图片；不能从加密 PDF 中提取内容 |
| **适用对象** | 财务人员、行政人员、需要将纸质发票数字化的个人或团队 |

## 二、触发方式与场景映射

| 触发词 | 适用场景 |
|--------|----------|
| `invoice-ocr-extract` | 命令行直接调用 |
| `发票识别` | 需要从发票图片中提取信息 |
| `发票提取` | 批量处理多张发票 |
| `OCR发票` | 使用 OCR 技术识别发票内容 |
| `发票结构化` | 需要将发票信息转为表格数据 |
| `票据解析` | 处理非标准格式的票据 |

## 三、标准执行流程

### 前置条件

1. 已安装 Python 3.8 或更高版本
2. 已安装依赖库：`pytesseract`、`Pillow`、`pdf2image`、`pandas`
3. 发票图片清晰、光线充足、发票平整无折痕
4. 发票文件格式为 JPG、PNG 或 PDF

### 执行步骤

1. **保存脚本**：将 `run.py` 保存到本地工作目录
2. **赋予执行权限**（可选）：
   ```bash
   chmod +x run.py
   ```
3. **单文件处理**：
   ```bash
   python run.py --input invoice.jpg --format json
   ```
4. **批量处理**：
   ```bash
   python run.py --batch --input ./invoices_dir/ --format csv
   ```
5. **设置置信度阈值**：
   ```bash
   python run.py --input invoice.png --threshold 0.8
   ```

### 输出规范

- **CSV 格式**（默认）：每行一张发票，列包含所有字段及置信度
- **JSON 格式**：嵌套结构，每张发票为一个对象，字段含 `value` 和 `confidence`
- **控制台输出**：处理完成后显示汇总统计（成功数、失败数、平均置信度）

## 四、置信度门控机制

当识别结果的置信度低于设定阈值（默认 0.8）时，系统不会直接输出该字段值，而是以 `[需核实:字段名]` 占位。例如：

```json
{
  "invoice_number": {"value": "[需核实:发票号码]", "confidence": 0.62},
  "total_amount": {"value": "1234.56", "confidence": 0.95}
}
```

**处理原则**：
- 置信度 ≥ 0.9：直接输出
- 置信度 0.8~0.9：输出并附带提示
- 置信度 < 0.8：输出占位符，建议人工复核

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件不存在 | 未找到指定文件，请检查路径 | 确认文件路径是否正确，文件名是否包含特殊字符 |
| `E002` | 格式不支持 | 不支持的文件格式，仅支持 JPG/PNG/PDF | 转换文件格式后重试 |
| `E003` | OCR 引擎未安装 | 未检测到 Tesseract OCR，请先安装 | 安装 `tesseract-ocr` 并配置环境变量 |
| `E004` | PDF 加密 | PDF 文件已加密，无法读取 | 使用密码解密后重新处理 |
| `E005` | 识别率过低 | 图片质量差，识别字段少于 3 个 | 重新拍摄或扫描发票，确保清晰平整 |
| `E006` | 批量目录为空 | 指定目录下没有符合条件的文件 | 检查目录路径和文件扩展名 |

## 六、常见坑与反模式对照

| 反模式 | 问题描述 | 正确做法 |
|--------|----------|----------|
| 直接拍摄反光发票 | 反光导致文字识别失败 | 使用扫描仪或调整拍摄角度，避免反光 |
| 批量处理混合格式 | 不同格式发票混在一起，识别率波动大 | 按发票类型分目录存放，分别处理 |
| 忽略置信度直接入账 | 低置信度字段可能导致财务数据错误 | 对置信度低于 0.8 的字段一律人工复核 |
| 使用压缩过度的图片 | 图片分辨率过低，小字无法识别 | 确保图片宽度不低于 1500 像素 |
| 依赖单一字段判断 | 仅凭发票号码判断识别是否成功 | 至少核对 3 个关键字段（号码、日期、金额） |

## 七、渐进式披露路径

### 新手路径（5 分钟上手）

1. 阅读「能力边界速查卡」了解基本功能
2. 使用单文件处理命令测试一张发票
3. 查看 CSV 输出，确认字段是否完整
4. 遇到问题参考「错误码体系」排查

### 进阶路径（深度使用）

1. 掌握批量处理与目录组织技巧
2. 理解置信度门控机制，设置合理的阈值
3. 使用 JSON 格式对接下游系统
4. 结合 `--threshold` 参数优化人工复核工作量
5. 根据识别结果反馈调整拍摄/扫描标准

### 参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | string | 必填 | 输入文件路径或目录 |
| `--batch` | flag | false | 启用批量模式 |
| `--format` | string | `csv` | 输出格式：`csv` 或 `json` |
| `--threshold` | float | `0.8` | 置信度阈值 |
| `--output` | string | 控制台 | 输出文件路径 |
| `--selftest` | flag | false | 运行自检 |
| `--version` | flag | false | 显示版本号 |

## 八、使用建议

1. **图片质量**：确保图片清晰、光线充足、发票平整，可显著提高识别准确率
2. **批量处理**：将发票文件放在同一目录下，使用 `--batch` 参数一次性处理
3. **置信度阈值**：建议对置信度低于 0.8 的结果进行人工复核
4. **输出格式**：需要程序化处理时使用 `--format json`，需要人工查看时使用默认 CSV

---

## 用户协议

<!-- user-agreement-injected -->

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。包括但不限于因识别错误、数据不准确、操作失误等造成的直接或间接损失。
2. **禁止反向工程**：不得对本 Skill 的代码、算法、模型进行反向工程、反编译、破解或试图提取源代码。
3. **合法使用**：使用者应确保使用本 Skill 处理的数据来源合法，不得用于侵犯他人隐私、知识产权或违反法律法规的活动。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。
5. **服务变更**：本 Skill 可能随时更新或终止，恕不另行通知。

---

## 许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 知微技能工坊

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

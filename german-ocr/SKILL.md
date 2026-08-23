---
slug: german-ocr
name: german-ocr
displayName: 德文票据字段抽取
description: 从德文票据、表单、证件中自动提取关键字段，输出结构化数据。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 结构化文档工坊
agent_created: true
trigger_words: ["发票识别", "德文OCR", "票据识别", "German OCR", "德文单据提取", "德文凭证解析", "德语票据结构化"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 德文票据字段抽取 Skill 文档

## 一、能力边界速查卡

本 Skill 用于从德文版式的票据、表单、证件图像中抽取关键业务字段，并输出为结构化数据。以下用一页纸说明其能力范围与限制。

### 1.1 能做什么

| 能力项 | 说明 | 支持程度 |
|--------|------|----------|
| 字段抽取 | 日期、金额、发票号、税号、收款方、付款方 | 核心能力 |
| 版式适配 | 横版、竖版、倾斜角 < 15° 的扫描件 | 支持 |
| 色彩适配 | 浅色背景上的深色文字 | 支持 |
| 批量处理 | 多张图片或一个多页 PDF，按页返回独立结果 | 支持 |
| 置信度标注 | 每个字段附带 0~1 置信度分数 | 支持 |
| 自定义字段映射 | 用户指定额外字段名（如 `bestellnummer`），按语义匹配抽取 | 支持 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 手写体识别 | 仅支持印刷体，手写内容不保证识别 |
| 复杂表格还原 | 不重建表格结构，仅抽取字段值 |
| 倾斜 > 15° 的图像 | 超出角度范围不保证准确率 |
| 深色背景浅色文字 | 反色版式不支持 |
| 多语言混合 | 仅针对德文为主的内容，其他语言字段可能漏抽 |
| 语义理解 | 不推断字段含义，仅按模式匹配抽取 |

### 1.3 适用对象

- 德文发票（Rechnung）
- 德文订单确认单（Auftragsbestätigung）
- 德文送货单（Lieferschein）
- 德文表单（Formular）
- 德文证件（Ausweis，仅限印刷体字段）

---

## 二、触发方式与场景映射

### 2.1 触发词

以下任一说法均可触发本 Skill：

- 发票识别
- 德文OCR
- 票据识别
- German OCR
- 德文单据提取
- 德文凭证解析
- 德语票据结构化

### 2.2 场景映射表

| 用户说（大白话） | 实际触发动作 |
|------------------|--------------|
| "帮我把这张德国发票上的金额和日期弄出来" | 执行字段抽取，输出结构化 JSON |
| "这批 PDF 是德国供应商的账单，批量提取一下" | 批量处理多页 PDF，按页返回结果 |
| "这个单据上有个订单号，帮我抓出来" | 自定义字段映射，提取 `bestellnummer` |
| "识别一下这张票据，看看有没有税号" | 抽取税号字段（USt-IdNr. / Steuernummer） |

---

## 三、标准执行流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| 文件格式 | JPG、PNG、TIFF、PDF（多页） |
| 文件大小 | 单张 ≤ 10 MB，PDF ≤ 50 MB |
| 分辨率 | ≥ 150 DPI，建议 300 DPI |
| 文件命名 | 建议统一前缀，如 `invoice_001.jpg` |
| 目录结构 | 待处理文件放入同一目录，避免路径含空格 |

### 3.2 执行步骤

1. **准备输入**：将待处理文件放入同一目录，确认命名规范一致。
2. **试运行**：先用单个样本执行，核对输出字段与格式。
3. **批量执行**：确认无误后对全量数据执行，并保留原始文件备份。
4. **校验结果**：抽查输出条目，核对关键字段与源数据一致。

### 3.3 输出规范

输出为 JSON 数组，每个元素对应一页/一张图的结果：

```json
[
  {
    "page": 1,
    "fields": {
      "datum": { "value": "2024-03-15", "confidence": 0.98 },
      "betrag": { "value": "1250.00 EUR", "confidence": 0.95 },
      "rechnungsnummer": { "value": "RE-2024-0315", "confidence": 0.92 },
      "ust_idnr": { "value": "DE123456789", "confidence": 0.88 },
      "empfaenger": { "value": "Muster GmbH", "confidence": 0.90 },
      "absender": { "value": "Lieferant AG", "confidence": 0.85 }
    },
    "warnings": []
  }
]
```

字段命名规范：

| 字段名 | 含义 | 示例 |
|--------|------|------|
| `datum` | 单据日期 | 2024-03-15 |
| `betrag` | 总金额 | 1250.00 EUR |
| `rechnungsnummer` | 发票号 | RE-2024-0315 |
| `ust_idnr` | 增值税号 | DE123456789 |
| `empfaenger` | 收款方 | Muster GmbH |
| `absender` | 付款方 | Lieferant AG |
| `bestellnummer` | 订单号（自定义） | 1000234 |

---

## 四、置信度门控机制

### 4.1 置信度阈值

| 置信度区间 | 处理方式 |
|------------|----------|
| 0.90 ~ 1.00 | 正常输出，标记为高置信 |
| 0.70 ~ 0.89 | 正常输出，附带提示"建议人工复核" |
| 0.50 ~ 0.69 | 输出值，同时标记 `[需核实:字段名]` |
| < 0.50 | 不输出值，仅输出 `[需核实:字段名]` 占位 |

### 4.2 占位符规则

当信息不足或置信度过低时，**不编造内容**，按以下格式输出：

```json
{
  "fields": {
    "datum": { "value": "[需核实:datum]", "confidence": 0.0 }
  }
}
```

### 4.3 信息缺失处理

- 字段在图像中不存在 → 输出 `null`，不猜测
- 字段存在但模糊 → 输出 `[需核实:字段名]`
- 字段存在但格式异常 → 输出原始文本 + 低置信度

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件格式不支持 | "文件格式不支持，请使用 JPG/PNG/TIFF/PDF" | 转换格式后重试 |
| `E002` | 文件过大 | "文件超过大小限制（单张 10MB / PDF 50MB）" | 压缩图片或拆分 PDF |
| `E003` | 分辨率过低 | "图像分辨率不足，建议 ≥ 150 DPI" | 重新扫描或更换原图 |
| `E004` | 倾斜角度过大 | "图像倾斜超过 15°，无法准确识别" | 手动校正后重试 |
| `E005` | 未检测到文本 | "未检测到可识别的德文文本" | 确认图像内容与背景对比度 |
| `E006` | 批量处理中断 | "第 N 页处理失败，已跳过，其余页正常输出" | 单独处理失败页 |
| `E007` | 自定义字段无匹配 | "未找到与 '字段名' 匹配的内容" | 检查字段名拼写或改用标准字段 |

---

## 六、FAQ 与反模式对照

### 6.1 常见坑

| 坑 | 反模式（错误做法） | 正确做法 |
|----|--------------------|----------|
| 手写体识别 | 直接提交手写填写的表单 | 改用印刷体版本，或人工录入 |
| 反色图像 | 提交深底白字的扫描件 | 转换为浅底深字后提交 |
| 多语言混合 | 提交中德混合的票据 | 确认主体语言为德文 |
| 低分辨率截图 | 用手机拍屏幕截图 | 使用原始 PDF 或高分辨率扫描 |
| 自定义字段拼写错误 | 提交 `bestell-nummer` 带连字符 | 使用标准拼写 `bestellnummer` |

### 6.2 反模式对照表

| 场景 | 错误操作 | 推荐操作 |
|------|----------|----------|
| 批量处理前 | 不试跑直接全量执行 | 先单样本验证，再批量 |
| 输出校验 | 不抽查直接入库 | 至少抽查 10% 输出条目 |
| 原始文件 | 处理后删除原图 | 保留原始文件备份至少 30 天 |
| 置信度处理 | 忽略低置信度标记 | 对 `[需核实:字段]` 逐条人工确认 |

---

## 七、渐进式阅读路径

### 7.1 速查卡（30 秒上手）

1. 把图片/PDF 放进一个文件夹
2. 说"识别这张德文发票"
3. 拿到 JSON 结果，检查置信度
4. 低置信度字段人工复核

### 7.2 新手路径（首次使用）

- 阅读「能力边界速查卡」→ 确认文件符合要求
- 按「标准执行流程」第 1~2 步，先跑一个样本
- 对照「输出规范」理解 JSON 结构
- 遇到问题查「错误码体系」

### 7.3 进阶路径（深度使用）

- 自定义字段映射：在请求中附加 `extra_fields: ["bestellnummer", "lieferdatum"]`
- 批量处理优化：统一文件命名，按批次执行，输出后自动校验
- 置信度调优：根据业务需求调整阈值（默认 0.7 为复核线）
- 结果后处理：将 JSON 导入数据库或 Excel，建立字段映射表

---

## 八、参数参考表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `file_path` | string | 必填 | 待识别文件路径 |
| `extra_fields` | array | `[]` | 自定义字段名列表 |
| `confidence_threshold` | float | `0.7` | 人工复核阈值 |
| `page_range` | string | `"all"` | 指定页范围，如 `"1-3"` |
| `output_format` | string | `"json"` | 输出格式，支持 `json` / `csv` |

---

## 九、用户协议

<!-- user-agreement-injected -->

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担全部责任。因使用本 Skill 产生的任何直接或间接损失，Skill 作者及发布平台不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取底层算法。
3. **数据合规**：使用者须确保所处理的文档具有合法获取与使用权限，遵守适用的数据保护法规（如 GDPR）。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

本 Skill 采用 MIT 许可证发布。

```
MIT License

Copyright (c) 2024 结构化文档工坊

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

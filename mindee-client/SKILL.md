---
slug: mindee-client
name: mindee-client
displayName: 票据识别 字段提取 数据化
description: 调用Mindee API解析票据，自动提取关键字段并输出结构化数据。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据管道工
agent_created: true
trigger_words: ["识别", "票据解析", "OCR提取", "-ocr", "票据数据化", "发票识别", "单据结构化"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# Mindee 票据识别与字段提取 Skill 文档

## 1. 能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入要求 | 输出形态 |
|--------|------|----------|----------|
| 票据识别 | 调用 Mindee API 对图片/PDF 进行 OCR 识别 | 单张图片（JPG/PNG/PDF） | JSON 结构化字段 |
| 字段提取 | 从识别结果中抽取关键业务字段（如发票号、金额、日期） | 已识别的 JSON 响应 | 精简后的字段映射表 |
| 批量处理 | 对同一目录下的多个文件逐一执行识别 | 目录路径 + 文件命名规范 | 每文件对应一个 JSON 输出 |
| 结果校验 | 抽查输出条目与源文件关键字段的一致性 | 输出 JSON + 源文件 | 校验报告（通过/存疑） |

### 1.2 不能做什么（明确边界）

- **不处理模糊或低分辨率图片**：若图片文字无法辨认，API 返回空字段，本 Skill 不进行图像增强。
- **不识别手写体**：Mindee 标准模型主要针对印刷体，手写内容识别率无保证。
- **不进行跨票据关联**：仅对单张票据独立提取，不合并多张票据的字段。
- **不保证字段完整性**：若票据本身缺少某字段（如无税号），输出中该字段为 `null`，不进行推测填充。
- **不处理非票据类文档**：如合同、身份证、名片等，超出本 Skill 适用范围。

### 1.3 适用对象

- 需要将纸质或电子票据（发票、收据、订单小票）转化为结构化数据的个人或团队。
- 已有 Mindee API 密钥，且文件已本地化存储的场景。
- 对数据准确性有抽查机制，而非完全依赖自动化的流程。

---

## 2. 触发方式与场景映射

### 2.1 触发词

| 触发词 | 场景示例（大白话） |
|--------|-------------------|
| 识别 | “帮我把这张发票识别一下” |
| 票据解析 | “这批收据需要解析出金额和日期” |
| OCR提取 | “这个 PDF 里的文字能提取出来吗” |
| -ocr | 命令行直接调用，如 `mindee-client -ocr invoice.jpg` |
| 票据数据化 | “把这几张小票变成 Excel 能用的数据” |
| 发票识别 | “识别这张增值税发票的所有字段” |
| 单据结构化 | “把订单确认单转成 JSON 格式” |

### 2.2 命令行接口

```bash
# 识别单张文件
mindee-client 识别 path/to/file.jpg

# 批量识别目录下所有文件
mindee-client 票据解析 path/to/directory/

# 自检命令
mindee-client --selftest

# 版本信息
mindee-client --version
```

---

## 3. 标准流程

### 3.1 前置条件

| 条件项 | 要求 | 检查方式 |
|--------|------|----------|
| Mindee API 密钥 | 有效且未过期 | 环境变量 `MINDEE_API_KEY` 已设置 |
| 文件格式 | JPG/PNG/PDF，单文件 ≤ 10MB | 文件大小与扩展名检查 |
| 文件命名 | 建议 `YYYYMMDD_类型_序号.ext`，如 `20250115_发票_001.jpg` | 目视或脚本检查 |
| 目录结构 | 待处理文件统一放在 `./input/`，输出到 `./output/` | 目录存在性检查 |
| 网络连通 | 可访问 Mindee API 端点 | `curl -I https://api.mindee.net` |

### 3.2 执行步骤（分步编号）

1. **环境准备**：确认 `MINDEE_API_KEY` 已导出，检查 `input/` 与 `output/` 目录存在。
2. **单样本试运行**：选取 `input/` 中一个代表性文件，执行 `mindee-client 识别 input/样本.jpg`，检查输出 JSON 中关键字段（如 `total_amount`、`invoice_number`）是否与源文件一致。
3. **核对输出格式**：确认输出 JSON 结构符合预期（见 3.3 输出规范），字段名无拼写错误。
4. **批量执行**：确认无误后，执行 `mindee-client 票据解析 input/`，对所有文件逐一识别。
5. **保留备份**：批量执行前，将 `input/` 目录复制为 `input_backup_日期/`，防止原始文件意外覆盖。
6. **结果抽查**：从输出中随机抽取 10%（至少 3 个）文件，人工核对关键字段与源文件的一致性。

### 3.3 输出规范

输出为 JSON 格式，每个文件对应一个 `.json` 文件，命名与源文件相同（扩展名替换为 `.json`）。结构如下：

```json
{
  "source_file": "20250115_发票_001.jpg",
  "processed_at": "2025-01-15T10:30:00Z",
  "api_response_id": "abc123def456",
  "fields": {
    "invoice_number": {"value": "INV-2025-001", "confidence": 0.98},
    "total_amount": {"value": 1250.00, "confidence": 0.95},
    "issue_date": {"value": "2025-01-10", "confidence": 0.99},
    "vendor_name": {"value": "某供应商有限公司", "confidence": 0.88}
  },
  "raw_response": { }
}
```

**字段说明**：
- `source_file`：源文件名。
- `processed_at`：处理时间（ISO 8601 格式）。
- `api_response_id`：Mindee API 返回的唯一标识，用于追溯。
- `fields`：提取的关键字段，每个字段包含 `value` 和 `confidence`（0-1 之间的置信度）。
- `raw_response`：Mindee API 的完整原始响应，保留用于调试。

---

## 4. 置信度门控

### 4.1 置信度阈值

| 置信度范围 | 处理方式 |
|------------|----------|
| ≥ 0.90 | 直接采用，标记为 `high_confidence` |
| 0.70 - 0.89 | 采用但标记为 `medium_confidence`，建议人工复核 |
| < 0.70 | 不采用，输出 `[需核实:字段名]` 占位符 |

### 4.2 占位符规则

当某个字段无法提取或置信度低于阈值时，输出中该字段的 `value` 设为 `[需核实:字段名]`，`confidence` 设为 `0`。示例：

```json
"tax_amount": {"value": "[需核实:tax_amount]", "confidence": 0}
```

**禁止行为**：不得根据其他字段推测缺失值，不得编造不存在的字段内容。

---

## 5. 错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | API 密钥无效或缺失 | “未检测到有效的 Mindee API 密钥，请检查环境变量 MINDEE_API_KEY。” | 1. 确认密钥已导出；2. 检查密钥是否过期；3. 重新生成密钥。 |
| `E002` | 文件格式不支持 | “文件格式不支持，仅接受 JPG、PNG、PDF。” | 1. 转换文件格式；2. 重新执行。 |
| `E003` | 文件大小超限 | “文件超过 10MB 限制，请压缩后重试。” | 1. 压缩图片或 PDF；2. 重新执行。 |
| `E004` | 网络连接失败 | “无法连接 Mindee API，请检查网络。” | 1. 检查网络连通性；2. 重试；3. 若持续失败，联系网络管理员。 |
| `E005` | API 返回空结果 | “API 未返回任何字段，可能图片质量过低或非票据类文档。” | 1. 检查图片清晰度；2. 确认文档类型；3. 更换样本重试。 |
| `E006` | 批量处理中断 | “批量处理在第 N 个文件处中断，请查看日志。” | 1. 查看错误日志定位具体文件；2. 修复该文件问题；3. 从断点继续。 |

---

## 6. FAQ 反模式

### 6.1 常见坑与反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 跳过试运行直接批量 | 直接对全量文件执行，导致错误格式蔓延 | 先用单个样本验证输出格式，再批量执行 |
| 忽略置信度标记 | 将 `medium_confidence` 字段直接入库 | 对置信度 < 0.90 的字段进行人工复核 |
| 覆盖原始文件 | 批量执行后删除 `input/` 目录 | 始终保留原始文件备份，至少保留 30 天 |
| 不检查 API 响应 ID | 无法追溯某条数据的来源 | 保存 `api_response_id`，便于问题回溯 |
| 对低质量图片强行识别 | 反复重试同一张模糊图片 | 接受 `[需核实:字段]` 结果，或人工录入 |

### 6.2 反模式示例

**错误做法**：
```bash
# 直接批量处理，不试运行
mindee-client 票据解析 input/
```

**正确做法**：
```bash
# 先试运行单个文件
mindee-client 识别 input/样本.jpg
# 检查输出无误后，再批量处理
mindee-client 票据解析 input/
```

---

## 7. 渐进式披露

### 7.1 速查卡（30 秒上手）

1. 设置密钥：`export MINDEE_API_KEY=你的密钥`
2. 放入文件：将待识别文件放入 `input/` 目录
3. 试运行：`mindee-client 识别 input/样本.jpg`
4. 检查输出：确认 `output/样本.json` 字段正确
5. 批量执行：`mindee-client 票据解析 input/`
6. 抽查结果：随机核对 10% 输出文件

### 7.2 分层次阅读路径

**新手路径**（首次使用）：
- 阅读第 1 节（能力边界）→ 第 3.1 节（前置条件）→ 第 7.1 节（速查卡）→ 第 6 节（FAQ 反模式）

**进阶路径**（熟练使用）：
- 阅读第 3.3 节（输出规范）→ 第 4 节（置信度门控）→ 第 5 节（错误码体系）→ 第 3.2 节（执行步骤细节）

**调试路径**（遇到问题）：
- 阅读第 5 节（错误码体系）→ 第 6 节（FAQ 反模式）→ 第 4 节（置信度门控）

---

## 8. 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于数据准确性、合规性及业务决策后果。本 Skill 提供的识别结果仅供参考，不构成任何形式的专业建议。
2. **禁止反向工程**：不得对本 Skill 的代码、逻辑、提示词结构进行反向工程、反编译、破解或试图提取底层算法。
3. **数据安全**：使用者应自行确保上传至 Mindee API 的数据符合相关法律法规及隐私政策，本 Skill 不承担数据泄露责任。
4. **服务可用性**：本 Skill 依赖第三方 Mindee API 服务，其可用性、稳定性及准确性由 Mindee 官方负责，本 Skill 不对其服务中断或结果错误负责。
5. **修改与分发**：使用者可在遵守 MIT 许可证的前提下修改和分发本 Skill，但需保留原始版权声明。

<!-- user-agreement-injected -->

---

## 9. 许可证（License）

本 Skill 采用 MIT 许可证授权。

### MIT License

```
MIT License

Copyright (c) 2025 数据管道工

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

## 10. 版本记录

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0.0 | 2025-01-15 | 初始版本，包含基础识别流程、置信度门控、错误码体系及合规章节。 |

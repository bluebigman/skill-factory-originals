---
slug: laravel-ocr
name: laravel-ocr
displayName: 票据识别 结构化抽取 置信评分
description: 将票据图片或链接解析为结构化JSON字段，附置信度评分。
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
trigger_words: ["文档识别", "OCR", "票据解析", "文档抽取", "结构化提取", "发票识别", "表单转JSON"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 票据结构化识别 Skill 文档

## 一、能力边界速查卡

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 图片解析 | 从 PNG/JPEG 图片中提取文字并转为 JSON | 发票、收据、行程单 |
| 链接解析 | 从公开图片 URL 下载并解析 | https://example.com/receipt.jpg |
| 字段映射 | 将识别文本映射为预定义 JSON 字段 | 金额、日期、发票号 |
| 置信度输出 | 每个字段附带 0~1 的置信度分数 | `{"amount": {"value": 100.00, "confidence": 0.95}}` |
| 批量处理 | 单次调用可传入多张图片（上限 5 张） | 一次解析 3 张发票 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不支持 BMP 格式 | 请先转换为 PNG 或 JPEG |
| 不处理手写体 | 仅支持印刷体文字识别 |
| 不进行语义理解 | 只提取字段，不判断业务逻辑（如是否重复报销） |
| 不保证 100% 准确 | 低质量图片可能产生低置信度结果，需人工复核 |
| 不存储任何图片 | 解析完成后立即丢弃原始图片数据 |

### 1.3 适用对象

- 财务人员：快速录入报销票据
- 行政人员：归档合同与收据
- 开发者：将 OCR 能力集成到业务系统

---

## 二、触发方式与场景映射

### 2.1 触发词

直接使用以下任一说法即可激活：

- "文档识别"
- "OCR"
- "票据解析"
- "文档抽取"
- "结构化提取"
- "发票识别"
- "表单转JSON"

### 2.2 场景映射表

| 用户说（大白话） | 实际执行动作 |
|------------------|--------------|
| "帮我把这张发票转成 JSON" | 调用图片解析，输出结构化字段 |
| "这个链接里的收据帮我提取一下" | 下载链接图片，执行解析 |
| "识别一下这张表格" | 按表格模板提取字段 |
| "批量处理这几张票据" | 循环调用解析，合并输出 |

---

## 三、标准执行流程

### 3.1 前置条件检查

| 检查项 | 要求 | 不满足时的处理 |
|--------|------|----------------|
| 图片分辨率 | ≥ 300 DPI | 提示用户更换高分辨率图片 |
| 图片格式 | PNG / JPEG | 提示转换格式 |
| 图片对比度 | 文字与背景可区分 | 提示调整亮度/对比度 |
| 倾斜角度 | ≤ 5° | 提示先进行倾斜校正 |
| 链接可访问 | 返回 200 且为图片 | 提示链接无效 |

### 3.2 执行步骤

1. **接收输入**：确认用户提供的是图片路径、Base64 编码还是 URL 链接。
2. **格式校验**：检查文件扩展名与 MIME 类型，拒绝 BMP/TIFF。
3. **预处理**（如需要）：
   - 若分辨率不足，提示用户；
   - 若倾斜超限，建议用户先校正。
4. **执行 OCR**：调用底层识别引擎，获取原始文本与坐标信息。
5. **字段映射**：根据预定义模板（见 3.3）将文本映射为 JSON 字段。
6. **置信度计算**：每个字段根据字符清晰度、位置匹配度计算 0~1 的分数。
7. **输出结果**：返回结构化 JSON，格式见 3.4。

### 3.3 字段映射模板（默认）

```json
{
  "invoice_number": "发票号码",
  "date": "开票日期",
  "amount": "价税合计",
  "seller_name": "销售方名称",
  "buyer_name": "购买方名称",
  "tax_amount": "税额"
}
```

### 3.4 输出规范

```json
{
  "status": "success",
  "data": {
    "invoice_number": {"value": "12345678", "confidence": 0.98},
    "date": {"value": "2024-03-15", "confidence": 0.95},
    "amount": {"value": 1000.00, "confidence": 0.92},
    "seller_name": {"value": "某某科技有限公司", "confidence": 0.88},
    "buyer_name": {"value": "某某商贸有限公司", "confidence": 0.90},
    "tax_amount": {"value": 130.00, "confidence": 0.85}
  },
  "warnings": ["seller_name 置信度偏低，建议人工核对"]
}
```

---

## 四、置信度门控机制

### 4.1 置信度阈值

| 置信度区间 | 处理方式 |
|------------|----------|
| 0.90 ~ 1.00 | 直接输出，无需复核 |
| 0.70 ~ 0.89 | 输出并附带 warning 提示 |
| 0.50 ~ 0.69 | 输出并标记 `needs_review: true` |
| < 0.50 | 不输出该字段，替换为 `[需核实:字段名]` 占位 |

### 4.2 占位符规则

当信息不足或置信度过低时，使用以下格式：

```json
{
  "amount": {"value": "[需核实:amount]", "confidence": 0.0}
}
```

**严禁**：在置信度不足时编造字段值。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E1001` | 图片格式不支持 | "仅支持 PNG 或 JPEG 格式" | 转换格式后重试 |
| `E1002` | 图片分辨率过低 | "分辨率低于 300 DPI，识别准确率可能下降" | 更换高分辨率图片 |
| `E1003` | 链接无法访问 | "链接返回 404 或超时" | 检查链接有效性 |
| `E1004` | 未识别到文字 | "图片中未检测到印刷体文字" | 确认图片内容 |
| `E1005` | 字段映射失败 | "无法将识别文本映射到模板字段" | 检查模板配置 |
| `E2001` | 批量处理超限 | "单次最多处理 5 张图片" | 分批处理 |

---

## 六、FAQ 与反模式对照

### 6.1 常见坑

| 坑 | 反模式（错误做法） | 正确做法 |
|----|-------------------|----------|
| 低分辨率图片 | 直接解析，结果大量错误 | 先提示用户更换图片 |
| 倾斜图片 | 忽略倾斜，直接解析 | 建议先校正再解析 |
| 手写票据 | 期望识别手写内容 | 明确告知仅支持印刷体 |
| 多张票据混拍 | 期望自动分割 | 提示用户单张拍摄 |
| 模板不匹配 | 强行映射字段 | 输出 `[需核实]` 占位 |

### 6.2 反模式示例

**反模式 1**：用户上传一张模糊的收据照片，直接解析并输出低置信度结果，不提示用户。

**正确做法**：先检查分辨率，若低于阈值，直接返回 `E1002` 错误码并建议重新拍摄。

**反模式 2**：识别结果中金额字段置信度仅 0.3，仍输出 `"amount": 100.00`。

**正确做法**：输出 `"amount": {"value": "[需核实:amount]", "confidence": 0.3}`。

---

## 七、渐进式披露阅读路径

### 7.1 速查卡（30 秒上手）

1. 上传 PNG/JPEG 图片或提供链接
2. 等待解析完成
3. 获取 JSON 结果，检查置信度
4. 低置信度字段人工复核

### 7.2 新手路径（完整阅读）

- 阅读「能力边界速查卡」了解限制
- 阅读「标准执行流程」掌握调用方式
- 阅读「置信度门控」理解输出规则

### 7.3 进阶路径（深度使用）

- 自定义字段映射模板（修改 3.3 节 JSON）
- 批量处理优化（控制并发与顺序）
- 集成到业务系统（处理错误码与重试逻辑）

---

## 八、参数配置参考

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `min_resolution` | int | 300 | 最低分辨率要求（DPI） |
| `max_batch_size` | int | 5 | 单次批量处理上限 |
| `confidence_threshold` | float | 0.5 | 字段输出最低置信度 |
| `warn_threshold` | float | 0.7 | 触发 warning 的置信度阈值 |
| `output_format` | string | "json" | 输出格式，仅支持 json |
| `timeout` | int | 30 | 链接下载超时时间（秒） |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因使用本 Skill 产生的任何直接或间接损失，包括但不限于数据错误、业务中断、法律纠纷，均由使用者自行承担。
2. **禁止反向工程**：不得对本 Skill 的底层算法、模型权重、提示词结构进行反向工程、反编译、破解或试图提取源代码。
3. **合规使用**：使用者应确保使用场景符合当地法律法规，不得将本 Skill 用于任何非法用途。
4. **数据安全**：使用者应自行确保上传图片中不包含敏感个人信息。本 Skill 不承担数据泄露责任。
5. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

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

---

*本文档由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*

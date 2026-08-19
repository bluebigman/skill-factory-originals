---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ambition
name: ambition
displayName: 文本转JSON 结构化提取 字段标注
description: 将非结构化文本智能转换为结构化JSON，自动识别字段并标注置信度。
version: 2.0.4
rules_version: cpr-20260819-n551
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ambition
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 结构化数据工坊
agent_created: true
trigger_words: ["文本转JSON", "结构化提取", "字段识别", "置信度标注", "批量转换", "数据清洗", "非结构化处理"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# ambition — 文本转JSON结构化提取专家

## 一、能力边界：一页纸速查卡

### 1.1 能做什么（✅ 支持范围）

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 纯文本转JSON | 将非结构化文本转换为键值对结构 | 简历、发票、合同条款 |
| 自动字段识别 | 基于上下文语义识别实体与属性 | 姓名、金额、日期、编号 |
| 置信度标注 | 每个字段附带0-1的置信度分数 | `"confidence": 0.92` |
| 批量处理 | 支持多文档并行转换 | 一次处理10份发票 |
| 多编码容错 | 自动检测并处理UTF-8/GBK/GB2312等编码 | 乱码自动修复 |
| 自定义Schema | 允许用户指定输出字段模板 | 仅提取金额与日期 |

### 1.2 不能做什么（❌ 明确拒绝）

| 限制项 | 说明 |
|--------|------|
| 非文本输入 | 不接受PDF/图片/音频等原始格式，需先经OCR或转录 |
| 语义推理 | 不进行跨句逻辑推断，仅基于显式文本信息 |
| 情感分析 | 不输出情感倾向或主观判断 |
| 实时流处理 | 不支持流式输入，需完整文本块 |
| 多语言混合 | 单次处理建议单一语言，混合语言可能降低准确率 |

### 1.3 适用对象

- **目标用户**：数据分析师、后端开发者、业务运营人员、文档处理自动化需求方
- **输入要求**：UTF-8编码的纯文本，单条不超过10,000字符
- **输出格式**：标准JSON，含`data`与`meta`两个顶层键

---

## 二、触发方式：场景映射表

| 触发词/场景 | 用户意图 | 处理策略 |
|-------------|----------|----------|
| "把这段文字转成JSON" | 通用转换需求 | 自动识别字段，输出完整JSON |
| "提取发票里的金额和日期" | 定向提取 | 按指定字段过滤输出 |
| "批量处理这些文本" | 多文档处理 | 逐条转换，汇总输出数组 |
| "这个文本乱码了" | 编码问题 | 先修复编码，再执行转换 |
| "帮我整理这些简历信息" | 结构化整理 | 按预设Schema提取候选人信息 |
| "合同里的关键条款提取" | 法律文档处理 | 识别条款编号、责任方、期限 |

---

## 三、标准流程：从输入到输出

### 3.1 前置条件

1. 输入文本已通过OCR或转录转换为可编辑文本
2. 文本编码为UTF-8（其他编码将自动尝试转换）
3. 单条文本长度不超过10,000字符
4. 如需自定义Schema，请提前准备字段清单

### 3.2 执行步骤

**Step 1：文本预处理**
- 去除多余空白字符与不可见字符
- 检测并统一编码（UTF-8/GBK/GB2312自动识别）
- 分段处理：按段落或逻辑块切分

**Step 2：字段识别**
- 基于预训练模型识别实体（人名、日期、金额、编号等）
- 结合上下文推断字段名（如"张三"→`name`）
- 生成候选字段列表及置信度

**Step 3：结构组装**
- 将识别结果组织为嵌套JSON结构
- 重复字段合并为数组
- 关联字段组合为对象

**Step 4：置信度标注**
- 每个字段附带`confidence`属性（0.0-1.0）
- 置信度阈值：≥0.9直接输出；0.7-0.9标注"需人工复核"；<0.7标记为`[需核实:字段名]`

**Step 5：输出生成**
- 返回标准JSON格式
- 包含`data`（提取结果）与`meta`（处理元信息）

### 3.3 输出规范

```json
{
  "data": {
    "name": {
      "value": "张三",
      "confidence": 0.95
    },
    "date": {
      "value": "2024-03-15",
      "confidence": 0.88
    },
    "amount": {
      "value": "12,500.00",
      "confidence": 0.91
    }
  },
  "meta": {
    "processed_at": "2026-08-19T10:30:00Z",
    "input_length": 256,
    "field_count": 3,
    "encoding": "UTF-8",
    "warnings": ["date字段格式需人工确认"]
  }
}
```

---

## 四、置信度门控机制

### 4.1 置信度分级

| 置信度区间 | 处理方式 | 输出标记 |
|-----------|----------|----------|
| 0.90-1.00 | 直接输出 | 无特殊标记 |
| 0.70-0.89 | 输出并提示复核 | `"needs_review": true` |
| 0.00-0.69 | 不输出具体值 | `"[需核实:字段名]"` |

### 4.2 信息不足时的处理

当无法从文本中提取某个字段时：
1. 不猜测、不编造
2. 输出占位符 `[需核实:字段名]`
3. 在`meta.warnings`中列出所有缺失字段
4. 提供缺失字段的上下文线索（如"文本中未找到日期信息"）

### 4.3 边界值说明

- 文本长度<10字符：返回错误码`ERR_SHORT_INPUT`
- 文本长度>10,000字符：截断处理并警告
- 字段值长度>500字符：截断并标记`"truncated": true`
- 单条文本字段数>50：拆分处理并提示

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `ERR_SHORT_INPUT` | 输入过短 | "输入文本过短，无法提取有效字段" | 提供至少10字符的文本 |
| `ERR_ENCODING` | 编码无法识别 | "无法识别文本编码，请转换为UTF-8" | 手动转换编码后重试 |
| `ERR_NO_FIELDS` | 未识别到任何字段 | "未从文本中识别到有效字段" | 检查文本是否包含实体信息 |
| `ERR_SCHEMA_MISMATCH` | 自定义Schema不匹配 | "自定义字段与文本内容不匹配" | 调整Schema或使用自动识别 |
| `ERR_BATCH_LIMIT` | 批量处理超限 | "单次批量处理最多支持50条文本" | 分批处理 |
| `ERR_TIMEOUT` | 处理超时 | "处理超时，请缩短文本长度" | 分段处理长文本 |

---

## 六、FAQ 反模式对照

### 常见坑1：过度依赖自动识别
- **反模式**：直接使用自动识别结果，不进行人工复核
- **正确做法**：对置信度<0.9的字段进行人工确认，特别是金额、日期等关键信息

### 常见坑2：忽略编码问题
- **反模式**：输入乱码文本直接转换，得到错误结果
- **正确做法**：先检查文本可读性，乱码时先进行编码修复

### 常见坑3：Schema设计不合理
- **反模式**：自定义Schema字段过细或过粗，导致提取失败
- **正确做法**：字段粒度适中，预留扩展空间，避免嵌套过深

### 常见坑4：批量处理不设上限
- **反模式**：一次性提交大量文本，导致超时或内存溢出
- **正确做法**：分批处理（每批≤50条），设置合理超时时间

### 常见坑5：忽略元信息
- **反模式**：只关注`data`部分，忽略`meta`中的警告信息
- **正确做法**：检查`meta.warnings`，处理所有标记的异常情况

---

## 七、渐进式披露：分层次阅读路径

### 7.1 速查卡（30秒上手）

```
输入：纯文本 → 输出：JSON
核心操作：自动识别字段 + 置信度标注
关键参数：confidence阈值（0.7/0.9）
错误处理：ERR_前缀错误码 + 修正建议
批量限制：单批≤50条，单条≤10,000字符
```

### 7.2 新手路径（首次使用）

1. 准备UTF-8编码的纯文本
2. 调用转换接口，使用默认自动识别
3. 检查输出JSON的`data`部分
4. 查看`meta.warnings`中的提示
5. 对置信度<0.9的字段进行人工确认

### 7.3 进阶路径（深度使用）

1. 设计自定义Schema，指定需要提取的字段
2. 调整置信度阈值（默认0.7/0.9，可按需修改）
3. 使用批量处理接口，配合错误码处理异常
4. 结合`meta`信息优化输入文本质量
5. 对高频场景建立模板，复用Schema配置

---

## 八、参数配置参考

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `confidence_threshold_high` | float | 0.90 | 高置信度阈值 |
| `confidence_threshold_low` | float | 0.70 | 低置信度阈值 |
| `max_input_length` | int | 10000 | 单条最大字符数 |
| `max_batch_size` | int | 50 | 单批最大条数 |
| `encoding_detection` | bool | true | 是否自动检测编码 |
| `custom_schema` | object | null | 自定义字段模板 |
| `output_format` | string | "json" | 输出格式（json/compact） |
| `include_meta` | bool | true | 是否包含元信息 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用前请仔细阅读以下条款：**

1. **责任承担**：使用者自行承担使用本Skill产生的全部责任。本Skill提供的输出结果仅供参考，不构成任何专业建议或决策依据。

2. **禁止反向工程**：未经授权，不得对本Skill进行反向工程、反编译、破解或试图提取源代码。

3. **数据安全**：使用者应确保输入数据不包含敏感个人信息或受保护数据。本Skill不承担数据泄露责任。

4. **合规使用**：使用者应遵守所在地区法律法规，不得将本Skill用于非法目的。

5. **免责声明**：本Skill按"现状"提供，不提供任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权保证。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 结构化数据工坊

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

*本Skill由AI辅助生成，仅供参考。使用前请阅读相关文档。*
<!-- ai-generated-notice -->

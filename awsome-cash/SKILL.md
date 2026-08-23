---
slug: awsome-cash
name: awsome-cash
displayName: 财务流水 智能解析 批量整理
description: 将杂乱财务数据解析为规范JSON，支持批量处理与置信度标注。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据工匠
agent_created: true
trigger_words: ["数据清洗", "结构化转换", "财务数据解析", "批量格式化", "流水整理", "账目整理", "对账处理", "财务规范化"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# awsome-cash — 财务流水智能解析与结构化输出

本 Skill 由 AI 辅助生成，仅供参考。它帮助你将格式混乱的财务流水（CSV、文本、网页表格）转换为结构统一的 JSON 数据，并为每条记录标注可信度，方便后续人工复核或程序化处理。

---

## 一、能力边界速查卡（先读这一节）

| 维度 | 说明 |
|------|------|
| ✅ 能做 | 解析 CSV / 纯文本格式的收支流水；识别日期、金额、收支方向、交易对手、摘要等常见字段；批量处理同一目录下的多个文件；从公开网页 URL 中提取表格数据；输出带 `confidence` 置信度标注的 JSON |
| ❌ 不能做 | 识别图片/PDF 中的扫描件（需先 OCR 转文本）；自动补全缺失的金额或日期（只会标注 `[需核实:字段]`）；判断交易是否合规或给出财务建议；连接银行 API 获取实时数据 |
| 🎯 适用对象 | 个人记账整理、小型商户流水归档、运营人员对账预处理、数据分析师做数据清洗前置步骤 |
| ⚠️ 不适用场景 | 需要审计级精度的财务报表、涉及多币种复杂汇率换算、需要法律效力的交易凭证生成 |

**输入要求**：文本或 CSV 文件，每行一条交易记录，字段间以逗号、制表符或竖线分隔；或提供包含表格的公开网页 URL。

---

## 二、触发方式与场景映射

当你的请求中包含以下意图时，本 Skill 会被激活：

| 你说的话（示例） | 触发意图 |
|------------------|----------|
| "帮我把这个 CSV 里的流水整理成 JSON" | 结构化转换 |
| "这几张表数据太乱了，清洗一下" | 数据清洗 |
| "把上个月的账单批量格式化" | 批量格式化 |
| "这个网页里的表格能提取出来吗" | URL 表格提取 |
| "对账用的，整理成统一格式" | 流水整理 / 对账处理 |

---

## 三、标准执行流程

### 前置条件

- 数据文件为 `.csv`、`.txt` 格式，或提供可公开访问的网页 URL
- 文件编码建议为 UTF-8（若为 GBK 请先转换）
- 单文件建议不超过 5MB，单次批量不超过 20 个文件

### 执行步骤

1. **确认输入类型**：告知是文件路径、目录路径还是网页 URL。
2. **字段映射**：系统自动识别常见字段别名（如 `日期/时间/date` → `date`；`金额/amount/交易额` → `amount`；`备注/摘要/description` → `description`）。若字段无法识别，默认归入 `raw_text` 字段保留原文。
3. **解析与清洗**：去除空行、合并被错误拆分的行、标准化日期格式（统一为 `YYYY-MM-DD`）、金额统一为数字类型（去除货币符号和千分位逗号）。
4. **生成 JSON 输出**：每条记录包含以下结构：

```json
{
  "date": "2024-11-15",
  "amount": 128.50,
  "direction": "expense",
  "counterparty": "某电商平台",
  "description": "办公用品采购",
  "raw_text": "2024/11/15 128.5 某电商平台 办公用品",
  "confidence": 0.95
}
```

5. **置信度标注**：`confidence` 取值范围 0~1。规则如下：
   - 0.9 以上：所有字段均明确匹配
   - 0.7~0.9：部分字段为推断值（如方向根据金额正负推断）
   - 0.7 以下：存在缺失或模糊字段，对应位置输出 `[需核实:字段名]` 占位符

### 输出规范

- 默认输出为 JSON 数组，每个元素对应一条交易记录
- 批量处理时，输出为 `{ "file_name": [记录数组], ... }` 的映射结构
- 所有输出均包含 `confidence` 字段，低于 0.7 的记录会在输出末尾附上人工复核清单

---

## 四、置信度门控机制

本 Skill 遵循"宁缺毋滥"原则：

- 当某字段无法从原文中可靠提取时，**不会猜测或编造**，而是输出 `[需核实:字段名]` 占位符。
- 例如：原文只有 `"11/15 128.5 电商"`，没有年份信息，则输出 `"date": "[需核实:年份]"`，且该条记录 `confidence` 降至 0.6。
- 若整条记录超过 3 个字段无法确认，该记录 `confidence` 设为 0.3，并单独标记 `"needs_review": true`。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件格式不支持 | "仅支持 .csv 和 .txt 文本文件" | 转换格式后重试 |
| `E002` | 文件编码无法识别 | "检测到非 UTF-8 编码，请转换编码" | 使用文本编辑器另存为 UTF-8 |
| `E003` | 字段分隔符无法自动检测 | "无法识别分隔符，请指定（逗号/制表符/竖线）" | 在请求中明确分隔符类型 |
| `E004` | 空文件或无有效数据行 | "文件中未找到可解析的数据行" | 检查文件内容是否为空 |
| `E005` | URL 无法访问或非公开 | "无法访问该 URL，请确认链接公开可读" | 更换为公开链接或下载后上传 |
| `E006` | 批量处理中部分文件失败 | "以下文件解析失败：xxx.csv（原因：E002）" | 根据子错误码单独处理失败文件 |

---

## 六、FAQ 与反模式对照

| 常见坑（反模式） | 正确做法 |
|------------------|----------|
| ❌ 直接粘贴 Excel 表格内容（含合并单元格） | ✅ 先另存为 CSV 或纯文本，确保每行一条记录 |
| ❌ 要求"把缺失的金额补上" | ✅ 接受 `[需核实:金额]` 占位符，事后人工补充 |
| ❌ 期望识别手写笔记照片 | ✅ 先使用 OCR 工具转成文本再提交 |
| ❌ 一次提交 50 个文件且不说明目录结构 | ✅ 将文件放入同一目录，或分批提交 |
| ❌ 要求输出"绝对准确"的结果 | ✅ 理解 `confidence` 机制，对低置信度记录进行复核 |

---

## 七、渐进式披露阅读路径

### 🆕 新手快速上手（30 秒）

1. 准备一个 CSV 文件，第一行是表头（如 `日期,金额,备注`）。
2. 直接说："解析这个文件：`/path/to/file.csv`"。
3. 拿到 JSON 输出后，检查 `confidence` 低于 0.7 的字段，手动确认。

### 🔧 进阶用户（3 分钟）

1. **自定义字段映射**：如需将 `counterparty` 改为 `merchant`，可在请求中说明："将交易对手字段命名为 merchant"。
2. **批量处理**：将多个文件放入 `/data/raw/` 目录，说："解析这个目录下所有 CSV"。
3. **URL 提取**：提供公开网页链接（如银行对账单公开示例页），说："提取这个页面里的表格"。
4. **自动化集成**：本 Skill 输出为标准 JSON，可直接通过管道传递给 pandas 或其他数据处理工具。示例：

```python
import json, subprocess
result = subprocess.run(["skill", "parse", "input.csv"], capture_output=True, text=True)
data = json.loads(result.stdout)
# 后续二次加工...
```

5. **周期性对账**：将本 Skill 嵌入定时任务，每日自动解析新增流水文件，输出 JSON 供对账脚本使用。

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的数据处理结果仅供参考，不构成任何形式的财务建议或法律意见。对于因数据解析错误、信息遗漏或使用不当造成的任何损失，本 Skill 作者及发布平台不承担任何责任。

2. **禁止反向工程**：不得对本 Skill 的底层逻辑、提示词结构、评分机制进行反向工程、处理、篡改或二次分发。不得尝试提取本 Skill 的内部算法或核心实现。

3. **数据合规**：使用者应确保提交的数据不包含违反法律法规的内容，不侵犯第三方隐私或知识产权。涉及个人财务数据的处理，使用者应自行确保符合相关数据保护法规。

4. **服务变更**：本 Skill 可能随时更新或下线，不另行通知。使用者应自行备份重要数据。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

本 Skill 采用 MIT 许可证发布：

```
MIT License

Copyright (c) 2024 数据工匠

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

*文档版本：1.0.0 | 最后更新：2024年12月*

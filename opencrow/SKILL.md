---
slug: opencrow
name: opencrow
displayName: 开放众包 数据解析 结构化输出
description: 将用户提供的文件或链接解析为规范结构化结果，支持批量与置信度标注。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: skillcraft-studio
agent_created: true
trigger_words: ["opencrow", "开放众包", "数据解析", "结构化输出", "批量处理"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# opencrow 技能文档

## 一、能力边界速查卡

本技能面向需要将非结构化数据（文本、表格、网页链接）转换为规范结构化结果的场景。以下是能力边界一览：

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入类型 | 文本片段、CSV/JSON 文件、公开 URL | 加密文件、需登录的私有系统、二进制大文件（>50MB） |
| 处理能力 | 关键信息提取、字段映射、格式转换、批量处理 | 语义推理、情感分析、跨语言翻译（仅保留原文） |
| 输出形式 | 结构化 JSON/Markdown 表格、自定义字段模板 | 生成图表、执行代码、直接写入外部数据库 |
| 质量保障 | 置信度标注、字段完整性校验、格式校验 | 保证 100% 准确率、替代人工审核 |

**适用对象**：需要快速将零散数据整理为统一格式的开发者、数据分析师、运营人员。

**不适用对象**：需要深度语义理解、创造性写作、法律/医疗等专业领域最终裁决的场景。

---

## 二、触发方式与场景映射

当你的请求包含以下关键词或意图时，本技能将被激活：

| 触发词/短语 | 典型用户表述 | 技能响应 |
|-------------|--------------|----------|
| opencrow | "用 opencrow 处理这份数据" | 启动标准解析流程 |
| 开放众包 | "帮我把众包结果整理一下" | 识别众包数据格式并结构化 |
| 数据解析 | "解析这个 CSV 里的关键字段" | 按字段映射规则提取 |
| 结构化输出 | "转成 JSON 格式给我" | 按约定 schema 输出 |
| 批量处理 | "这 50 个文件都处理一遍" | 进入批量执行模式 |

**场景示例**：
- "我有一份用户反馈的 Excel，帮我提取反馈类型和紧急程度" → 触发解析+结构化输出
- "把这个网页里的产品列表抓下来，整理成表格" → 触发 URL 解析+表格生成

---

## 三、标准处理流程

### 前置条件

1. 确认输入文件与当前工作目录在同一路径下，或提供可访问的完整 URL。
2. 文件命名遵循 `[项目名]_[批次]_[日期].[扩展名]` 格式（如 `feedback_batch1_20250115.csv`）。
3. 明确输出目标格式（默认 JSON，可选 Markdown 表格）。

### 执行步骤

**步骤 1：输入解析**
- 读取文件内容或抓取 URL 文本。
- 识别数据边界：表头行、分隔符（逗号/制表符/竖线）、嵌套结构。
- 输出：解析后的原始数据字典。

**步骤 2：关键信息提取**
- 根据预设字段映射表（见下表）匹配关键字段。
- 对无法匹配的字段，标记为 `[需核实:字段名]` 占位。
- 保留原始文本作为 `_raw` 字段备查。

**步骤 3：结构化生成**
- 按目标 schema 重组数据。
- 每条记录附加 `_confidence` 字段（0-1 浮点数）。
- 置信度计算规则：
  - 所有字段均成功匹配 → 0.95
  - 存在 1-2 个占位字段 → 0.75
  - 存在 3 个以上占位字段 → 0.50

**步骤 4：校验与输出**
- 检查字段完整性：必填字段缺失时输出警告。
- 检查格式正确性：JSON 语法、日期格式（YYYY-MM-DD）、数字类型。
- 输出最终结果，并在文档末尾附处理日志。

### 输出规范

```json
{
  "schema_version": "1.0",
  "generated_at": "2025-01-15T10:30:00Z",
  "record_count": 3,
  "records": [
    {
      "id": "001",
      "fields": { "name": "张三", "type": "bug" },
      "_confidence": 0.95,
      "_raw": "原始文本..."
    }
  ],
  "warnings": ["记录 002 缺少 'priority' 字段"]
}
```

---

## 四、置信度门控机制

当遇到以下情况时，技能不会强行编造数据，而是明确标注：

| 情况 | 处理方式 | 示例 |
|------|----------|------|
| 字段缺失 | 输出 `[需核实:字段名]` 占位 | `"email": "[需核实:email]"` |
| 格式冲突 | 保留原始值并降低置信度 | 日期 `15/01/2025` 与 `2025-01-15` 并存时，取后者并标注 |
| 数据矛盾 | 两条记录冲突时，保留两条并标记 | `"_conflict": true` |
| 超出范围 | 数值超出预设边界（如年龄 > 120） | 标记 `[需核实:age]` 并附原始值 |

**规则**：任何 `[需核实:]` 占位出现时，该记录置信度上限为 0.75；占位超过 3 个时，上限为 0.50。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 文件不存在 | "未找到指定文件，请检查路径与文件名" | 1. 确认文件已放入工作目录；2. 检查扩展名大小写 |
| E002 | 格式无法解析 | "输入格式无法识别，请确认分隔符或结构" | 1. 尝试指定分隔符参数；2. 转为 CSV 或 JSON 后重试 |
| E003 | 字段映射失败 | "存在无法匹配的字段，已生成占位符" | 1. 查看 `_raw` 原始值；2. 手动补充映射规则 |
| E004 | 批量中断 | "第 N 个文件处理失败，已跳过并记录日志" | 1. 查看错误日志；2. 修复后从断点继续 |
| E005 | 输出校验失败 | "输出格式不符合 schema，请检查必填字段" | 1. 对比 schema 定义；2. 补齐缺失字段 |

---

## 六、FAQ 与反模式对照

| 常见坑（反模式） | 正确做法（模式） |
|------------------|------------------|
| 直接处理未备份的原始文件 | 始终保留原始文件副本，处理副本而非原件 |
| 一次性批量处理全部数据而不试运行 | 先用 1-2 条样本试运行，确认输出无误后再全量执行 |
| 忽略置信度标注，直接采用所有结果 | 对置信度 < 0.80 的记录进行人工复核 |
| 修改输入文件格式以适配技能 | 保持输入原样，通过参数调整解析规则 |
| 将 `[需核实:]` 占位当作最终结果提交 | 将占位字段替换为实际值或明确标注为待确认 |

---

## 七、渐进式阅读路径

### 新手快速上手（5 分钟）

1. 阅读「能力边界速查卡」了解适用范围。
2. 将待处理文件放入工作目录，命名规范。
3. 运行单样本测试：`opencrow --selftest` 验证环境。
4. 执行标准流程步骤 1-3，查看输出 JSON。

### 进阶用户指南（15 分钟）

1. 自定义字段映射：在配置文件中定义 `field_mapping` 规则。
2. 批量处理：使用 `--batch` 参数，配合错误码 E004 的断点续传。
3. 输出格式扩展：支持 YAML、XML 等自定义序列化格式。
4. 置信度阈值调整：通过 `--confidence-threshold` 参数控制过滤级别。

### 高级定制（30 分钟+）

1. 编写自定义校验脚本，挂载到步骤 4 的校验阶段。
2. 扩展字段类型系统：支持日期范围、枚举值、嵌套对象。
3. 集成外部数据源：通过 API 拉取补充信息填充占位字段。

---

## 八、命令行接口

```
opencrow [选项] <输入文件或URL>

选项：
  --selftest          运行自检，验证环境配置
  --version           显示版本信息
  --format <类型>     输出格式：json（默认）/ markdown / yaml
  --batch             批量处理目录下所有匹配文件
  --confidence-threshold <0-1>  低于该值的记录将被标记
  --config <路径>     指定配置文件
```

---

## 用户协议

使用本技能即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本技能产生的全部责任。本技能提供的输出结果仅供参考，不构成任何形式的专业建议或保证。
2. **禁止反向工程**：不得对本技能进行反向工程、反编译、破解或试图提取底层算法。
3. **合规使用**：使用者须确保输入数据来源合法，且处理过程符合当地法律法规。
4. **免责声明**：本技能按"原样"提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 许可证（License）

MIT License

Copyright (c) 2025 skillcraft-studio

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

<!-- professional-license-embedded -->

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: forgery
name: forgery
displayName: 数据伪造识别 字段提取 置信度标注
description: 将任意数据转为结构化结果，识别关键信息并标注置信度。
version: 1.0.2
rules_version: cpr-20260820-n601
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/forgery
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: DataForge Studio
agent_created: true
trigger_words: ["forgery", "伪造数据", "数据生成", "结构化转换", "字段提取", "数据清洗", "信息抽取"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# forgery — 数据伪造识别与结构化转换 Skill

## 一、能力边界：一页纸速查卡

本 Skill 的核心用途是：**将用户提供的任意数据（文件、文本、表格）转换为结构化结果，识别关键信息并标注置信度**。它不是一个通用数据生成器，也不是一个数据验证工具。

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 字段提取 | 从非结构化文本中抽取指定字段 | 从一段人物介绍中提取姓名、年龄、职业 |
| 结构化转换 | 将自由文本转为 JSON/表格格式 | 将一段商品描述转为 `{名称, 价格, 库存}` |
| 置信度标注 | 对每个提取字段给出可信程度 | `{"姓名": {"值": "张三", "置信度": 0.95}}` |
| 批量处理 | 对同一目录下的多个文件逐一执行 | 处理 `./data/*.txt` 中的所有文件 |
| 格式校验 | 检查输出是否符合预定义 schema | 校验字段是否齐全、类型是否正确 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不生成虚构数据 | 输入必须真实存在，本 Skill 不负责"编造"内容 |
| 不验证数据真实性 | 置信度仅反映提取过程的可靠程度，不代表数据本身正确 |
| 不处理图片/音频 | 仅支持文本类输入（.txt, .md, .csv, .json） |
| 不自动修复数据 | 发现缺失字段时输出占位符，不猜测填充 |

### 1.3 适用对象

- **适用**：日志文件、用户反馈、商品信息、简历文本、调查问卷等文本类数据
- **不适用**：二进制文件、加密数据、需要外部知识库补全的语义推断

---

## 二、触发方式：场景映射表

当你的指令中出现以下关键词或意图时，本 Skill 会被激活：

| 触发词/短语 | 实际场景举例 |
|-------------|--------------|
| "forgery" | "用 forgery 处理这个文件" |
| "伪造数据" | "帮我伪造一份测试数据"（注意：此处指生成结构化测试样本，非造假） |
| "数据生成" | "生成一个包含姓名和邮箱的 JSON" |
| "结构化转换" | "把这段文本转成表格" |
| "字段提取" | "从这些日志里提取时间戳和错误码" |
| "数据清洗" | "把这些杂乱的数据整理成统一格式" |
| "信息抽取" | "抽取出所有手机号" |

**大白话触发示例**：
- "帮我把这个 CSV 里的日期格式统一一下" → 触发结构化转换
- "这段对话里有哪些关键人物？" → 触发字段提取
- "这个文件夹里所有文件都按同样格式整理" → 触发批量处理

---

## 三、标准流程：从输入到输出

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 输入文件 | 文本格式（.txt/.md/.csv/.json） | 文件扩展名确认 |
| 文件位置 | 与 Skill 工作目录一致 | `ls` 查看 |
| 命名规范 | 文件名不含空格和特殊字符 | 正则 `^[a-zA-Z0-9_\-\.]+$` |
| 字段定义 | 用户需明确要提取哪些字段 | 对话确认或默认提取常见字段 |

### 3.2 执行步骤（分步编号）

1. **确认输入**：列出目标文件，核对命名规范，询问用户需要提取的字段列表（若未指定，使用默认字段集：`id`, `name`, `date`, `value`）。
2. **单样本试运行**：取第一个文件执行提取，输出 JSON 预览，与用户确认字段名和格式是否符合预期。
3. **调整 schema**：根据用户反馈修改字段映射规则（如日期格式 `YYYY-MM-DD`、数字保留两位小数）。
4. **批量执行**：对剩余文件逐一执行，每个文件生成独立输出文件（`原文件名.forged.json`）。
5. **结果校验**：随机抽查 3 个输出文件，核对关键字段与源数据一致性，输出校验报告。

### 3.3 输出规范

每个输出文件遵循以下 JSON 结构：

```json
{
  "source_file": "input_001.txt",
  "processed_at": "2026-08-20T14:30:00Z",
  "fields": [
    {
      "name": "姓名",
      "value": "张三",
      "confidence": 0.95,
      "source_location": "第2行第3列"
    },
    {
      "name": "年龄",
      "value": 28,
      "confidence": 0.87,
      "source_location": "第2行第5列"
    }
  ],
  "warnings": ["字段'邮箱'未找到，已置为[需核实:邮箱]"]
}
```

**字段说明**：
- `source_file`：源文件名
- `processed_at`：处理时间（ISO 8601）
- `fields[].name`：字段名（与用户确认的 schema 一致）
- `fields[].value`：提取的值（保持原始类型）
- `fields[].confidence`：置信度（0.0~1.0，保留两位小数）
- `fields[].source_location`：源文本中的位置描述
- `warnings`：处理过程中的异常说明

---

## 四、置信度门控：不编造原则

当提取过程中遇到以下情况时，**不得猜测或编造值**，必须输出占位符：

| 情况 | 占位符 | 示例 |
|------|--------|------|
| 字段在源数据中不存在 | `[需核实:字段名]` | `"邮箱": "[需核实:邮箱]"` |
| 字段存在但格式异常 | `[需核实:字段名]` + warning | 日期写成"昨天" |
| 多个候选值冲突 | `[需核实:字段名]` + 列出候选 | 两个不同的电话号码 |
| 置信度低于 0.5 | 保留提取值但标注低置信度 | `"confidence": 0.32` |

**置信度计算规则**：
- 0.9~1.0：字段在源文本中唯一出现且格式完全匹配
- 0.7~0.89：字段出现但格式略有偏差（如大小写不一致）
- 0.5~0.69：字段出现但上下文模糊（如多个同名实体）
- <0.5：无法确定，输出占位符

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件不存在 | "未找到文件 {filename}，请确认路径" | 检查文件名和目录，重新输入 |
| `E002` | 文件格式不支持 | "仅支持 .txt/.md/.csv/.json 格式" | 转换文件格式后重试 |
| `E003` | 字段定义为空 | "请至少指定一个要提取的字段" | 提供字段列表或使用默认字段 |
| `E004` | 输出目录不可写 | "无法写入输出文件，请检查权限" | 修改目录权限或更换输出路径 |
| `E005` | 批量处理中断 | "第 {n} 个文件处理失败，已跳过" | 查看错误详情，修复后重新执行 |
| `E006` | 置信度过低 | "字段 {field} 置信度低于阈值，已置为占位符" | 检查源数据，确认字段是否存在 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 忽略置信度 | 直接使用所有提取值，不看 confidence | 对置信度 <0.7 的字段进行人工复核 |
| 过度依赖默认字段 | 不指定字段就批量处理，导致输出无关信息 | 先与用户确认字段列表，再执行 |
| 覆盖原始文件 | 直接修改源文件，无备份 | 保留原始文件，输出到独立目录 |
| 一次性处理全部 | 未试运行直接批量执行，schema 错误导致返工 | 先单样本验证，再批量 |
| 忽略 warnings | 只关注 fields，不看 warnings 数组 | 检查 warnings，处理异常情况 |

---

## 七、渐进式披露：分层次阅读路径

### 速查卡（30 秒上手）

```
输入：文本文件 + 字段列表
流程：单样本试运行 → 确认 schema → 批量执行 → 校验
输出：JSON 文件（含置信度）
关键：置信度 <0.7 需人工复核；缺失字段输出 [需核实:xxx]
```

### 新手路径（5 分钟）

1. 阅读「能力边界」了解适用范围
2. 按「标准流程」执行一次单样本处理
3. 查看输出 JSON，理解 `confidence` 和 `warnings` 的含义
4. 遇到问题查「错误码体系」

### 进阶路径（15 分钟）

1. 深入理解「置信度门控」的计算规则，自定义阈值
2. 学习批量处理时的异常恢复策略（E005 处理）
3. 根据「FAQ 反模式」优化自己的使用习惯
4. 扩展字段提取规则，处理复杂格式（如嵌套 JSON、多行记录）

---

## 八、参数配置参考

| 参数 | 默认值 | 可选值 | 说明 |
|------|--------|--------|------|
| `confidence_threshold` | 0.7 | 0.0~1.0 | 低于此值的字段标记为需核实 |
| `output_format` | json | json/csv | 输出文件格式 |
| `date_format` | ISO 8601 | 任意合法格式 | 日期字段的解析格式 |
| `batch_size` | 10 | 1~100 | 批量处理时每批文件数 |
| `preserve_original` | true | true/false | 是否保留原始文件备份 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于数据处理的准确性、输出结果的合规性、以及因使用不当造成的任何损失。
2. **禁止反向工程**：不得对本 Skill 的底层逻辑、算法、提示词结构进行反向工程、反编译、破解或试图提取源代码。
3. **合法用途**：本 Skill 仅用于合法的数据处理目的。禁止用于生成虚假信息、伪造身份、规避安全检测等违法用途。
4. **无保证**：本 Skill 按"现状"提供，不附带任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权性。
5. **数据安全**：用户应对输入数据的合法性和敏感性负责。本 Skill 不承担数据泄露或隐私侵犯的责任。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 DataForge Studio

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*

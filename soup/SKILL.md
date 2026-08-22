---
slug: soup
name: soup
displayName: 数据汤 解析萃取 结构化输出
description: 将杂散数据解析为结构化结果，附置信度标注与批量处理能力。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["soup", "数据汤", "结构化输出", "数据解析", "批量处理", "信息萃取"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# 数据汤（soup）技能手册

## 一、能力边界速查卡

本技能面向需要将非结构化或半结构化数据转化为规范结构化结果的场景。适用对象包括：数据分析师、运维工程师、内容运营人员，以及任何需要从文本/文件/URL 中批量提取关键字段的开发者。

| 能做 ✅ | 不能做 ❌ |
|--------|----------|
| 解析用户提供的文本、文件、URL 内容 | 访问需登录鉴权的私有系统 |
| 识别并保留输入中的关键信息字段 | 对加密或损坏文件进行修复 |
| 按约定 schema 输出 JSON/YAML/CSV | 自动推断未明确指定的业务规则 |
| 对不确定字段输出置信度提示 | 保证解析结果 100% 准确 |
| 批量处理同目录下多个文件 | 处理超过单次上下文窗口的超大文件 |

**输入要求**：文本内容、UTF-8 编码的 .txt/.csv/.json/.md 文件，或可公开访问的 URL。
**输出默认格式**：JSON 对象数组，每个对象包含 `id`、`fields`、`confidence` 三个顶层键。

---

## 二、触发方式与场景映射

当你的请求中出现以下关键词或意图时，本技能将被激活：

| 触发词/短语 | 典型场景 |
|------------|---------|
| "soup" | 直接调用技能处理数据 |
| "数据汤" | 中文场景下的同义调用 |
| "把这段数据整理一下" | 非结构化文本转结构化 |
| "提取里面的关键信息" | 从长文中抽取指定字段 |
| "批量处理这些文件" | 多文件统一格式转换 |
| "结构化输出" | 要求按固定 schema 输出 |

**示例**：
- "用 soup 处理一下这个日志文件，提取时间戳和错误码"
- "数据汤，帮我从这堆 URL 里提取标题和发布日期"
- "批量处理 ./data/ 目录下的所有 csv，输出为 json"

---

## 三、标准处理流程

### 前置条件

1. 确认输入数据来源（文本粘贴 / 文件路径 / URL）
2. 确认输出格式（默认 JSON，可选 YAML/CSV）
3. 确认字段映射规则（若未指定，则自动识别常见字段）
4. 单次处理文件数 ≤ 50，单文件大小 ≤ 1MB

### 执行步骤

1. **输入接收**：读取用户提供的数据内容或文件内容。
2. **格式探测**：识别输入是纯文本、表格、日志、还是嵌套结构。
3. **字段识别**：根据上下文和常见模式（时间戳、邮箱、URL、金额等）提取候选字段。
4. **结构化组装**：将提取结果按 schema 组装为 JSON 对象。
5. **置信度标注**：对每个字段标注 `high` / `medium` / `low` 置信度。
6. **输出生成**：按用户指定格式输出结果。

### 输出规范

```json
[
  {
    "id": 1,
    "fields": {
      "timestamp": "2025-01-15T10:30:00Z",
      "error_code": "E404",
      "message": "Resource not found"
    },
    "confidence": {
      "timestamp": "high",
      "error_code": "high",
      "message": "medium"
    }
  }
]
```

**置信度判定规则**：

| 置信度 | 判定条件 |
|--------|---------|
| high | 字段值匹配明确模式（如 ISO 时间戳、标准状态码） |
| medium | 字段值存在但格式不标准，或存在多种可能解释 |
| low | 字段值缺失、模糊，或需要人工确认 |

---

## 四、置信度门控与占位符

当输入信息不足以确定某个字段值时，**不得编造或猜测**。此时输出 `[需核实:字段名]` 占位符，并在 `confidence` 中标记为 `low`。

**示例**：

```json
{
  "id": 3,
  "fields": {
    "author": "[需核实:author]",
    "date": "2025-03-01"
  },
  "confidence": {
    "author": "low",
    "date": "high"
  }
}
```

**处理原则**：
- 若某条记录超过 50% 字段为 `[需核实]`，整条记录标记为 `needs_review`。
- 若用户未指定字段映射，且自动识别失败，则输出原始文本片段并标注 `low`。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|---------|---------|
| `E001` | 输入为空 | "未检测到有效输入，请提供文本、文件路径或 URL" | 检查输入是否为空或格式错误 |
| `E002` | 文件不存在 | "指定路径下未找到文件，请确认路径是否正确" | 核对文件路径及文件名 |
| `E003` | 文件编码不支持 | "仅支持 UTF-8 编码文件，请转换后重试" | 使用 `iconv` 或文本编辑器转换编码 |
| `E004` | 字段映射冲突 | "检测到多个字段映射规则冲突，请明确指定" | 提供明确的字段映射表 |
| `E005` | 批量处理中断 | "批量处理在第 N 个文件处失败，已跳过该文件" | 检查失败文件格式，修复后单独重试 |
| `E006` | 输出格式不支持 | "仅支持 json/yaml/csv 三种输出格式" | 重新指定输出格式 |

---

## 六、常见坑与反模式对照

| 常见坑 ❌ | 反模式示例 | 正确做法 ✅ |
|----------|-----------|------------|
| 忽略置信度直接使用结果 | 把 `low` 置信度的字段直接写入数据库 | 对 `low` 字段进行人工复核或二次验证 |
| 输入超大文件导致超时 | 一次处理 100MB 日志文件 | 先拆分文件，分批处理 |
| 未指定字段映射导致误提取 | 自动识别把"日期"识别为"版本号" | 提前声明字段类型和格式 |
| 批量处理前不试运行 | 直接对 50 个文件执行，结果全错 | 先跑 1 个样本，核对无误后再全量执行 |
| 覆盖原始文件 | 输出直接写回原文件，数据丢失 | 输出到新文件，保留原始备份 |

---

## 七、渐进式阅读路径

### 新手路径（5 分钟上手）

1. 阅读「能力边界速查卡」了解基本能力。
2. 使用最简单的调用方式：粘贴一段文本，说"用 soup 处理"。
3. 查看输出 JSON 中的 `confidence` 字段，了解哪些结果可信。
4. 遇到 `[需核实]` 时，手动补充信息后重新处理。

### 进阶路径（深度使用）

1. 熟悉「标准处理流程」中的字段识别规则。
2. 自定义字段映射：提供 `字段名: 提取规则` 字典。
3. 使用批量处理：将文件放入同一目录，按命名规范统一处理。
4. 结合错误码体系，编写自动化处理脚本。
5. 对 `medium` 置信度的字段，设计二次校验逻辑。

---

## 八、批量处理操作指南

### 准备阶段

1. 创建输入目录 `./input/`，将所有待处理文件放入。
2. 确认文件命名规范：`data_01.txt`、`data_02.txt` 等。
3. 创建输出目录 `./output/`，用于存放结果。

### 执行阶段

```bash
# 单样本试运行
soup --input ./input/data_01.txt --output ./output/result_01.json

# 批量执行
soup --batch ./input/ --output ./output/ --format json
```

### 校验阶段

1. 抽查 5-10% 的输出条目，核对关键字段与源数据一致性。
2. 检查 `confidence` 分布：若 `low` 占比超过 30%，需调整字段映射规则。
3. 确认所有 `[需核实]` 占位符已人工处理。

---

## 九、命令行接口

```bash
soup --selftest    # 运行自检，验证环境配置
soup --version     # 显示版本信息
```

**自检输出示例**：

```
[OK] 输入解析模块正常
[OK] 字段识别模块正常
[OK] 置信度标注模块正常
[OK] 输出格式化模块正常
版本: 1.0.0
```

---

## 十、用户协议

使用本技能即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本技能产生的全部责任。本技能提供的所有输出仅供参考，不构成任何形式的专业建议或保证。
2. **禁止反向工程**：不得对本技能进行反向工程、反编译、破解或试图提取底层算法。
3. **合规使用**：使用者须确保输入数据来源合法，不得使用本技能处理违法违规内容。
4. **无担保声明**：本技能按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。
5. **服务变更**：技能作者保留随时修改、更新或终止本技能的权利，恕不另行通知。

<!-- user-agreement-injected -->

---

## 十一、许可证（License）

本技能采用 MIT 许可证授权：

```
MIT License

Copyright (c) 2025 LinguaForge

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证输出结果。*

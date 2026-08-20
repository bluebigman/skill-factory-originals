---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: soup
name: soup
displayName: 数据汤 结构化转换 批量解析
description: 将任意输入数据解析为结构化结果，支持批量处理与置信度标注。
version: 1.0.2
rules_version: cpr-20260820-n601
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/soup
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨
agent_created: true
trigger_words: ["soup", "数据汤", "结构化转换", "批量解析", "数据清洗", "数据整理", "格式归一化"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 数据汤（soup）技能手册

## 一、能力边界：一页纸速查卡

### 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 格式识别 | 自动识别 JSON、CSV、纯文本、日志等常见输入格式 | 一段混合了日期和金额的文本 → 拆分为字段 |
| 字段抽取 | 从非结构化文本中提取关键字段 | 从邮件正文中提取发件人、主题、日期 |
| 批量处理 | 支持多文件批量解析，统一输出格式 | 一个目录下 50 个 CSV 文件 → 合并为一个 JSON 数组 |
| 置信度标注 | 每个字段附带置信度分数，低置信度字段明确标记 | `{"name": "张三", "confidence": 0.95}` |
| 占位符机制 | 无法确定的字段输出 `[需核实:字段名]`，不编造 | `{"age": "[需核实:age]"}` |

### 不能做什么

| 禁止事项 | 说明 |
|----------|------|
| 不编造数据 | 绝不填充猜测值，缺失字段一律使用占位符 |
| 不推断语义 | 只做格式转换和字段抽取，不做情感分析或意图判断 |
| 不修改源文件 | 输入文件只读，所有输出写入 output/ 目录 |
| 不处理加密内容 | 加密文件、密码保护文档无法解析 |

### 适用对象

- 需要将散乱数据整理为统一格式的数据分析师
- 需要批量处理日志、导出文件的运维工程师
- 需要从非结构化文本中提取信息的业务人员

---

## 二、触发方式：场景映射表

| 你说的话 | 触发动作 | 示例输出 |
|----------|----------|----------|
| "soup 帮我解析这个文件" | 解析单个文件 | 结构化 JSON 输出 |
| "数据汤处理一下这批日志" | 批量解析目录下所有日志 | 合并后的 JSON 数组 + 处理报告 |
| "把这个 CSV 转成 JSON" | 格式转换 | 转换后的 JSON 文件 |
| "清洗一下这些数据" | 去重、格式归一化、缺失值标注 | 清洗后的数据集 + 清洗报告 |
| "soup --selftest" | 环境自检 | 环境检查报告 |
| "soup --version" | 版本查询 | 当前版本号 |

---

## 三、标准处理流程

### 前置条件

| 条件 | 要求 | 检查方法 |
|------|------|----------|
| 输入文件 | 文件编码为 UTF-8（或可自动识别） | `file -i 文件名` |
| 目录结构 | 输入文件与输出目录分离 | 确认 output/ 目录存在 |
| 环境验证 | 运行 `soup --selftest` 确认环境正常 | 返回 `ALL CHECKS PASSED` |

### 执行步骤

**第一步：准备**

将待处理文件放入同一目录，命名包含批次标识（如 `batch_20260820_01.csv`）。

**第二步：试跑**

先处理 1 个文件，检查输出是否符合预期：

```bash
soup --input ./data/batch_20260820_01.csv --output ./output/
```

检查输出 JSON 中的字段名、类型、置信度标注是否正确。

**第三步：批量**

试跑确认无误后，处理全部文件：

```bash
soup --input ./data/ --output ./output/ --batch
```

**第四步：校验**

随机抽查 10% 的输出文件，核对关键字段（如 ID、日期、金额）是否与源文件一致。

**第五步：交付**

确认无误后，将 output/ 目录下的结果文件和 processing_report.md 一并交付。

### 输出规范

所有输出遵循以下结构：

```json
{
  "source_file": "batch_20260820_01.csv",
  "parsed_at": "2026-08-20T14:30:00Z",
  "records": [
    {
      "id": "001",
      "name": "张三",
      "amount": 1500.00,
      "confidence": {
        "id": 0.99,
        "name": 0.95,
        "amount": 0.98
      }
    }
  ],
  "warnings": []
}
```

---

## 四、置信度门控机制

### 核心原则

**信息不足时，输出占位符，绝不编造。**

### 占位符规则

| 场景 | 输出值 | 置信度 | 警告 |
|------|--------|--------|------|
| 字段缺失 | `[需核实:字段名]` | `low` | 添加说明 |
| 字段格式异常 | `[需核实:字段名]` | `low` | 添加说明 |
| 字段值超出合理范围 | `[需核实:字段名]` | `low` | 添加说明 |
| 输入格式与描述严重不符 | 整个记录标记为 `unparsed` | `low` | 添加详细说明 |

### 置信度阈值

| 阈值 | 默认值 | 可通过环境变量调整 |
|------|--------|-------------------|
| 高置信度 | ≥ 0.9 | `SOUP_HIGH_THRESHOLD` |
| 中置信度 | 0.7 - 0.9 | `SOUP_MID_THRESHOLD` |
| 低置信度 | < 0.7 | `SOUP_LOW_THRESHOLD` |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件不存在 | "找不到输入文件，请检查路径" | 确认文件路径，检查文件名拼写 |
| `E002` | 文件编码不支持 | "无法识别文件编码，请转换为 UTF-8" | 使用 `iconv -f GBK -t UTF-8` 转换 |
| `E003` | 格式解析失败 | "无法解析输入格式，请检查文件内容" | 查看文件前 10 行，确认格式 |
| `E004` | 字段类型冲突 | "字段类型不一致，已标记为低置信度" | 检查源数据，统一字段类型 |
| `E005` | 批量处理中断 | "批量处理在第 N 个文件处中断" | 查看错误日志，修复后从第 N+1 个继续 |
| `E006` | 输出目录不可写 | "无法写入输出目录，请检查权限" | 检查目录权限，或更换输出路径 |
| `E007` | 环境依赖缺失 | "缺少必要依赖库，请运行 --selftest" | 运行 `soup --selftest` 查看缺失项 |

---

## 六、FAQ 反模式对照

### 常见坑 1：直接批量处理未试跑

**反模式**：跳过试跑步骤，直接处理全部文件，结果发现字段映射错误，全部返工。

**正确做法**：先处理 1 个文件，确认输出结构正确后再批量执行。

### 常见坑 2：忽略置信度标注

**反模式**：直接使用输出数据，未检查低置信度字段，导致下游分析出错。

**正确做法**：处理前先过滤 `confidence < 0.7` 的字段，人工核实后再使用。

### 常见坑 3：占位符当作真实值

**反模式**：将 `[需核实:字段名]` 当作字符串存入数据库，后续查询时产生脏数据。

**正确做法**：将占位符字段标记为 NULL 或单独存储，待人工补充后再合并。

### 常见坑 4：输入格式与描述不符

**反模式**：声称输入是 JSON，实际是 JSONL（每行一个 JSON 对象），导致解析失败。

**正确做法**：先运行 `soup --inspect 文件名` 查看格式检测结果，再决定处理方式。

### 常见坑 5：忽略警告信息

**反模式**：只关注输出结果，忽略 `warnings` 数组中的提示，遗漏数据质量问题。

**正确做法**：每次处理完成后，先查看 `warnings` 数组，逐条确认后再交付。

---

## 七、渐进式披露：分层次阅读路径

### 新手路径（5 分钟上手）

1. 阅读「一、能力边界」了解能做什么、不能做什么
2. 阅读「三、标准处理流程」按步骤执行
3. 遇到问题查「五、错误码体系」

### 进阶路径（深入使用）

1. 阅读「四、置信度门控机制」理解数据质量保障原理
2. 阅读「六、FAQ 反模式对照」避免常见错误
3. 阅读「八、高级配置」自定义输出模板和参数

### 专家路径（定制扩展）

1. 阅读「九、扩展指南」了解如何集成 CI/CD
2. 阅读「十、技术规格」了解底层实现细节
3. 阅读「用户协议」确认合规要求

---

## 八、高级配置

### 自定义输出模板

在输入时附带模板 JSON，指定字段映射：

```json
{
  "template": {
    "customer_id": "id",
    "customer_name": "name",
    "transaction_amount": "amount"
  }
}
```

### 环境变量参数

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `SOUP_CONFIDENCE_THRESHOLD` | 0.7 | 置信度阈值，低于此值的字段标记为 low |
| `SOUP_OUTPUT_FORMAT` | json | 输出格式，可选 json / csv / yaml |
| `SOUP_MAX_FILE_SIZE` | 10MB | 单文件大小上限 |
| `SOUP_BATCH_SIZE` | 100 | 批量处理时每批文件数 |

---

## 九、扩展指南

### 扩展输入类型

支持 XML、YAML、Markdown 表格等格式，通过插件机制扩展：

```bash
soup --input file.xml --format xml
```

### 集成 CI/CD

将本技能作为数据预处理步骤嵌入流水线：

```yaml
# .github/workflows/data-pipeline.yml
steps:
  - name: Parse data
    run: soup --input ./raw/ --output ./parsed/ --batch
```

### 自定义解析规则

通过配置文件定义字段抽取规则：

```yaml
# soup_rules.yaml
rules:
  - field: date
    pattern: "\\d{4}-\\d{2}-\\d{2}"
    type: date
  - field: amount
    pattern: "\\d+\\.\\d{2}"
    type: float
```

---

## 十、技术规格

### 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Linux / macOS / Windows |
| Python 版本 | ≥ 3.8 |
| 依赖库 | 见 requirements.txt |

### 性能指标

| 场景 | 处理速度 | 内存占用 |
|------|----------|----------|
| 单文件 1MB | < 1 秒 | < 50MB |
| 批量 100 个文件 | < 30 秒 | < 200MB |
| 单文件 100MB | < 10 秒 | < 500MB |

### 输出格式

所有输出遵循 JSON Schema：

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "source_file": {"type": "string"},
    "parsed_at": {"type": "string", "format": "date-time"},
    "records": {"type": "array"},
    "warnings": {"type": "array"}
  },
  "required": ["source_file", "parsed_at", "records", "warnings"]
}
```

---

## 用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即视为同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 仅提供数据处理辅助功能，不构成任何形式的数据处理承诺或保证。

2. **禁止反向工程**：使用者不得对本 Skill 的底层实现进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。

3. **合法用途**：本 Skill 仅供学习与参考用途，使用者不得将其用于任何违反法律法规或侵犯第三方权益的场景。

4. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

5. **协议更新**：本协议可能随时更新，更新后的版本将在本 Skill 文档中发布。继续使用本 Skill 即视为接受更新后的协议。

---

## 许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2026 林墨

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

*文档版本：1.0.0 | 最后更新：2026-08-20*

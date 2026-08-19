---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ai-content-generator-using-gpt-3-acg
name: acg-structured-text-processor
displayName: 文本批处理 规则引擎 结构化提取
description: 本地规则驱动的文本批处理与结构化提取工具，支持多格式输出与置信度标注。
version: 3.1.1
rules_version: cpr-20260819-n551
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ai-content-generator-using-gpt-3-acg
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨研
agent_created: true
trigger_words: ["文本批处理", "结构化提取", "规则引擎", "数据清洗", "格式转换", "批量处理"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# ACG 结构化文本处理器 — 技能文档

## 一、能力边界速查卡

本工具是一个**本地规则驱动的文本批处理与结构化提取引擎**。它不依赖云端 API，不进行语义理解，而是通过用户定义的规则（正则、字典、模板）对文本进行模式匹配、字段抽取和格式重组。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入格式 | 纯文本、JSON、Markdown、CSV | 扫描件 OCR、手写体识别 |
| 处理方式 | 规则匹配、字段提取、格式转换 | 语义理解、情感分析、意图识别 |
| 输出格式 | JSON、Markdown、CSV（带置信度） | 直接写入数据库（需二次开发） |
| 文件大小 | 建议 ≤ 50MB/文件，支持分块 | 超过 50MB 需先手动分块 |
| 编码支持 | UTF-8 及常见编码（GBK、Big5 等） | 二进制文件、加密文件 |
| 自定义能力 | 支持 `rules.json` 自定义规则 | 不支持运行时动态编译代码 |

**适用对象**：需要批量清洗日志、抽取合同关键字段、转换数据格式的开发者或数据分析师。不适合需要理解上下文语义的场景。

---

## 二、触发方式与场景映射

当你的任务涉及以下关键词时，可调用本技能：

| 触发词 | 典型场景 |
|--------|----------|
| 文本批处理 | 批量提取 1000 份日志中的 IP 地址和错误码 |
| 结构化提取 | 从非结构化报告中抽取日期、金额、负责人 |
| 规则引擎 | 按正则规则过滤敏感信息 |
| 数据清洗 | 去除 CSV 中的重复行和格式错误 |
| 格式转换 | 将 Markdown 表格转为 JSON 数组 |
| 批量处理 | 多文件统一提取字段并汇总 |

**大白话示例**：
- “帮我把这堆 txt 里的手机号都抠出来，按 CSV 存”——触发
- “把这几百个 JSON 里的 `name` 字段抽出来做成表格”——触发
- “理解一下这段话的感情色彩”——不触发（超出能力）

---

## 三、标准执行流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| 输入文件 | 文本格式，≤50MB（超过需分块） |
| 规则文件 | `rules.json`（可选，默认内置通用规则） |
| 运行环境 | Python 3.8+，安装 `acg-processor` 包 |
| 编码 | 默认 UTF-8，其他编码需指定 `--encoding` |

### 3.2 执行步骤

1. **预览模式验证规则**（必做）
   ```bash
   acg-processor --dry-run -i input.txt -r rules.json
   ```
   此命令不生成输出文件，仅打印前 10 条提取结果，用于确认规则是否命中。

2. **正式处理**
   ```bash
   acg-processor -i input.txt -o output.json -r rules.json --format json
   ```

3. **大文件分块处理**
   ```bash
   acg-processor -i big_file.txt -o out/ --chunk-size 10MB --format csv
   ```
   `--chunk-size` 按内存占用自动切分，每块独立处理，结果合并输出。

4. **置信度过滤**
   ```bash
   acg-processor -i input.txt -o clean.json --min-confidence 0.8
   ```
   低于 0.8 的记录将被丢弃，并在日志中标注 `[LOW_CONF]`。

5. **指定编码**
   ```bash
   acg-processor -i gbk_file.txt -o out.json --encoding gbk
   ```

### 3.3 输出规范

- **JSON 输出**：数组格式，每条记录含 `data`（提取字段）和 `confidence`（0-1 浮点数）。
- **Markdown 输出**：表格形式，第一行为字段名，末列固定为 `置信度`。
- **CSV 输出**：UTF-8 编码，带表头，置信度列名为 `confidence`。

**示例输出（JSON）**：
```json
[
  {
    "data": {"ip": "192.168.1.1", "error_code": "E404"},
    "confidence": 0.95
  }
]
```

---

## 四、置信度门控机制

当规则匹配不完整或字段缺失时，系统**不会编造数据**，而是执行以下策略：

| 情况 | 输出行为 |
|------|----------|
| 字段缺失 | 输出 `[需核实:字段名]` 占位符 |
| 置信度 < 0.5 | 丢弃该记录，日志记录原因 |
| 置信度 0.5-0.8 | 保留记录，标记 `[LOW_CONF]` |
| 规则冲突 | 取最高置信度规则结果，标注 `[CONFLICT]` |

**示例**：
```json
{"data": {"ip": "192.168.1.1", "error_code": "[需核实:error_code]"}, "confidence": 0.72}
```

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件不存在 | 输入文件路径无效，请检查 | 确认路径，使用绝对路径 |
| `E002` | 编码错误 | 文件编码与指定不符 | 使用 `--encoding` 指定正确编码 |
| `E003` | 规则语法错误 | `rules.json` 解析失败 | 用 `json.tool` 校验规则文件 |
| `E004` | 内存溢出 | 文件过大，超出可用内存 | 使用 `--chunk-size` 分块处理 |
| `E005` | 无匹配结果 | 规则未命中任何文本 | 检查规则正则，使用 `--dry-run` 调试 |
| `E006` | 输出格式冲突 | 指定格式与文件扩展名不符 | 统一 `--format` 与输出文件后缀 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 规则过宽 | 用 `.*` 匹配所有内容 | 使用锚点 `^...$` 和字符类 `[0-9]` |
| 忽略编码 | 直接处理 GBK 文件 | 先 `file` 命令检测编码，再指定 |
| 大文件硬跑 | 一次性加载 100MB 文件 | 分块处理，每块 ≤ 10MB |
| 不验证规则 | 直接全量处理 | 先 `--dry-run` 预览前 10 条 |
| 置信度一刀切 | 全部接受或全部拒绝 | 按业务需求设 `--min-confidence` |

---

## 七、渐进式阅读路径

### 新手路径（5 分钟上手）
1. 阅读「能力边界速查卡」确认工具适用性。
2. 使用内置规则跑一次 `--dry-run`。
3. 按「标准执行流程」第 2 步生成第一个输出文件。

### 进阶路径（深度定制）
1. 学习编写 `rules.json`（正则 + 字段映射）。
2. 理解置信度计算逻辑（规则命中率 × 字段完整率）。
3. 结合 `--chunk-size` 和 `--min-confidence` 处理生产级数据。

---

## 八、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本工具产生的全部责任，包括但不限于数据丢失、处理结果错误、合规风险。
2. **禁止反向工程**：不得对本 Skill 的规则引擎核心逻辑进行逆向工程、反编译或试图提取源代码。
3. **合规使用**：不得使用本工具处理违反法律法规的数据，包括个人隐私信息、受版权保护内容。
4. **无担保**：本工具按“现状”提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

本 Skill 采用 MIT 许可证发布。

```
MIT License

Copyright (c) 2026 林墨研

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

*文档版本：1.0.0 | 最后更新：2026-08-19*

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agency-agents
name: agency-agents
displayName: 多角色任务编排 结构化交付 批量处理
description: 将任意文本输入解析为结构化数据，支持批量处理、置信度标注与多格式输出。
version: 1.1.1
rules_version: cpr-20260812-n376
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agency-agents
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge Studio
agent_created: true
trigger_words: ["agency-agents", "多角色编排", "结构化交付", "批量解析", "任务编排"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


# agency-agents — 多角色任务编排与结构化交付工具

## 一、能力边界：一页纸速查卡

### 1.1 工具定位

`agency-agents` 是一个命令行工具，核心功能是将**自由文本输入**转换为**结构化数据**。它模拟多角色协作流程（如“提取→分类→校验→输出”），但实际执行时完全依赖本地规则引擎，不调用外部 AI 服务。

### 1.2 能做 / 不能做清单

| 维度 | ✅ 能做 | ❌ 不能做 |
|------|---------|-----------|
| **输入处理** | 读取文本文件，每行视为一条独立记录 | 不支持 PDF、Word、扫描件等二进制格式 |
| **解析能力** | 基于正则表达式与关键词规则，提取字段、打标签、分类 | 不执行语义理解、情感分析、上下文推理 |
| **批量操作** | 单次运行可处理数千行记录，输出结果与输入行一一对应 | 不维护跨批次状态，每次运行相互独立 |
| **置信度标注** | 每条输出记录附带 `confidence` 字段（0.0~1.0） | 置信度仅反映规则匹配强度，不代表真实准确率 |
| **输出格式** | 支持 JSON、CSV、JSONL 三种格式 | 不支持 XML、YAML 或自定义模板 |
| **扩展性** | 可通过修改规则文件（`rules.json`）调整解析逻辑 | 不支持插件机制或运行时动态加载代码 |

### 1.3 适用对象

- **数据清洗人员**：需要将杂乱的日志、评论、表单文本快速转为表格数据。
- **自动化流程开发者**：在 CI/CD 管道中嵌入文本预处理步骤。
- **业务分析师**：对批量反馈文本进行初步分类与关键词提取。
- **教育/研究用途**：演示规则引擎与结构化输出的基本概念。

### 1.4 已知限制

- 规则匹配基于字面模式，对同义词、俚语、拼写错误不敏感。
- 输出准确性依赖输入文本的规范性，非标准文本可能导致低置信度或字段缺失。
- 工具不提供图形界面，所有交互通过命令行完成。

---

## 二、触发方式与场景映射

### 2.1 触发词

- **主触发词**：`agency-agents`
- **同义场景词**：`多角色编排`、`结构化交付`、`批量解析`、`任务编排`

### 2.2 场景映射表

| 用户说（大白话） | 实际执行动作 | 对应命令 |
|------------------|--------------|----------|
| “帮我把这些评论按正面/负面分类” | 运行工具，使用内置情感词典规则 | `python run.py --input comments.txt --task classify` |
| “提取所有订单号和时间戳” | 运行工具，使用正则提取规则 | `python run.py --input logs.txt --task extract --fields order_id,timestamp` |
| “把结果转成 CSV 给我” | 运行工具，指定输出格式 | `python run.py --input data.txt --output result.csv --format csv` |
| “测试一下工具是否正常” | 运行自检程序 | `python run.py --selftest` |
| “查看版本号” | 显示版本信息 | `python run.py --version` |

---

## 三、标准流程：从安装到交付

### 3.1 前置条件

| 条件 | 要求 | 验证方法 |
|------|------|----------|
| Python 环境 | 3.8 及以上 | `python --version` |
| 依赖包 | 无（仅标准库） | — |
| 输入文件 | UTF-8 编码，每行一条记录 | `file -bi input.txt` |
| 磁盘空间 | 至少 10MB 可用空间 | `df -h` |

### 3.2 安装步骤

1. **获取脚本**：将 `run.py` 文件保存到目标工作目录（如 `/opt/agency-agents/`）。
2. **赋予执行权限（可选）**：
   ```bash
   chmod +x run.py
   ```
3. **验证安装**：
   ```bash
   python run.py --version
   ```
   预期输出：
   ```
   agency-agents version 1.0.0
   ```

### 3.3 执行步骤（分步编号）

1. **准备输入文件**：创建 `input.txt`，每行一条待处理记录。示例：
   ```
   订单#A1001 于2024-03-15发货，金额￥299
   用户反馈：物流太慢，差评
   [INFO] 2024-03-16 10:22:33 服务重启完成
   ```

2. **选择任务类型**：通过 `--task` 参数指定解析模式。
   | 任务类型 | 说明 | 示例规则 |
   |----------|------|----------|
   | `extract` | 提取指定字段 | 订单号、日期、金额 |
   | `classify` | 按关键词分类 | 正面/负面/中性 |
   | `tag` | 打标签 | 紧急、待处理、已完成 |

3. **运行工具**：
   ```bash
   python run.py --input input.txt --task extract --fields order_id,date,amount --output result.json --format json
   ```

4. **检查输出**：打开 `result.json`，每条记录包含 `raw_text`、`parsed_data`、`confidence` 三个字段。

5. **处理低置信度记录**：筛选 `confidence < 0.6` 的记录，人工复核。

### 3.4 输出规范

| 字段 | 类型 | 说明 |
|------|------|------|
| `raw_text` | string | 原始输入行 |
| `parsed_data` | object | 解析后的结构化字段，键为字段名，值为字符串或 null |
| `confidence` | float | 0.0~1.0，表示规则匹配强度 |
| `warnings` | array | 解析过程中的警告信息（如字段缺失） |

**JSON 输出示例**：
```json
{
  "raw_text": "订单#A1001 于2024-03-15发货，金额￥299",
  "parsed_data": {
    "order_id": "A1001",
    "date": "2024-03-15",
    "amount": "299"
  },
  "confidence": 0.95,
  "warnings": []
}
```

---

## 四、置信度门控机制

### 4.1 置信度计算规则

- **完全匹配**（所有字段均命中规则）：`confidence = 1.0`
- **部分匹配**（至少一个字段命中）：`confidence = 命中字段数 / 期望字段数`
- **零匹配**（无字段命中）：`confidence = 0.0`

### 4.2 信息不足时的处理

当输入文本无法满足字段提取要求时，工具**不会编造数据**，而是：

1. 在 `parsed_data` 中将缺失字段设为 `null`。
2. 在 `warnings` 数组中添加说明。
3. 输出占位符 `[需核实:字段名]` 到 `parsed_data` 对应键。

**示例**：
```json
{
  "raw_text": "订单#B2024 已发货",
  "parsed_data": {
    "order_id": "B2024",
    "date": "[需核实:date]",
    "amount": "[需核实:amount]"
  },
  "confidence": 0.33,
  "warnings": ["字段 date 未匹配到规则", "字段 amount 未匹配到规则"]
}
```

### 4.3 置信度阈值建议

| 使用场景 | 建议阈值 | 处理方式 |
|----------|----------|----------|
| 自动化管道 | 0.8 | 低于阈值自动丢弃或转人工队列 |
| 数据分析 | 0.6 | 低于阈值标记为“低质量”，分析时排除 |
| 人工复核 | 0.0~1.0 | 全部人工检查，阈值仅作参考 |

---

## 五、错误码体系

### 5.1 常见错误与修正

| 错误码 | 错误信息 | 可能原因 | 修正步骤 |
|--------|----------|----------|----------|
| `E001` | `Input file not found` | 输入文件路径错误 | 检查文件是否存在，使用绝对路径 |
| `E002` | `Invalid task type` | `--task` 参数值不在支持列表中 | 运行 `python run.py --help` 查看支持的任务类型 |
| `E003` | `Output format not supported` | `--format` 参数值不是 `json`/`csv`/`jsonl` | 重新指定格式，注意大小写 |
| `E004` | `Empty input file` | 输入文件为空或只有空行 | 检查文件内容，确保每行有有效文本 |
| `E005` | `Encoding error` | 文件不是 UTF-8 编码 | 使用 `iconv` 转换编码，或另存为 UTF-8 |
| `E006` | `Permission denied` | 输出目录无写入权限 | 使用 `chmod` 修改目录权限，或指定其他输出路径 |

### 5.2 错误提示话术

当发生错误时，工具会输出如下格式：
```
[ERROR] E001: Input file not found: /path/to/nonexistent.txt
建议：请检查文件路径是否正确，或使用 --help 查看参数说明。
```

### 5.3 自检模式

运行 `python run.py --selftest` 可执行内置测试用例，验证工具功能完整性。预期输出：
```
Self-test passed: 8/8 checks OK
```

---

## 六、FAQ 反模式对照

### 6.1 常见坑与正确做法

| 反模式（错误做法） | 后果 | 正确做法 |
|---------------------|------|----------|
| 输入文件包含空行或特殊字符 | 解析结果出现空记录或乱码 | 预处理输入文件，去除空行，统一编码 |
| 期望工具理解语义 | 输出结果与预期不符，置信度低 | 明确工具基于规则匹配，调整输入文本格式 |
| 忽略 `confidence` 字段 | 低质量数据混入分析结果 | 设置阈值过滤，或人工复核低置信度记录 |
| 修改 `rules.json` 后不测试 | 规则语法错误导致运行失败 | 修改后先运行 `--selftest` 验证 |
| 将工具用于非文本数据 | 无法处理，报错或输出空结果 | 确认输入为纯文本格式 |

### 6.2 反模式对照表

| 场景 | 反模式 | 推荐模式 |
|------|--------|----------|
| 处理中文文本 | 使用英文正则规则 | 在 `rules.json` 中添加中文关键词规则 |
| 处理超长文本（>1000字） | 整行输入 | 预先截断或分段处理 |
| 批量处理 10 万条记录 | 单次运行 | 分批处理，每批 1 万条，避免内存溢出 |
| 需要实时响应 | 每次运行都解析规则文件 | 将规则文件预加载到内存（需二次开发） |

---

## 七、渐进式披露：分层次阅读路径

### 7.1 速查卡（30 秒上手）

```bash
# 安装
python run.py --version

# 基本用法
python run.py --input input.txt --task extract --fields order_id,date

# 指定输出格式
python run.py --input input.txt --task classify --output result.csv --format csv

# 自检
python run.py --selftest
```

### 7.2 新手路径（首次使用）

1. 阅读「一、能力边界」了解工具能做什么。
2. 按照「三、标准流程」完成一次完整运行。
3. 查看输出 JSON 文件，理解 `parsed_data` 和 `confidence` 字段。
4. 遇到问题查阅「五、错误码体系」。

### 7.3 进阶路径（深度定制）

1. 阅读 `rules.json` 文件，理解规则结构（正则表达式、关键词列表）。
2. 修改规则以适配特定业务场景。
3. 使用 `--selftest` 验证规则修改的正确性。
4. 结合外部脚本（如 Python、Shell）实现自动化管道。

### 7.4 规则文件结构说明

`rules.json` 位于工具同目录下，结构如下：
```json
{
  "extract": {
    "order_id": "正则表达式",
    "date": "正则表达式",
    "amount": "正则表达式"
  },
  "classify": {
    "positive": ["好评", "满意", "推荐"],
    "negative": ["差评", "失望", "退货"]
  }
}
```

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用前请仔细阅读以下条款，使用本工具即视为同意本协议。**

1. **责任承担**：使用者自行承担因使用本工具产生的全部责任。包括但不限于数据丢失、业务中断、决策失误等直接或间接损失。本工具按“现状”提供，不提供任何形式的明示或暗示担保。

2. **禁止反向工程**：使用者不得对本工具进行反向工程、反编译、反汇编，或试图提取源代码（除非适用法律允许）。不得移除或修改任何版权声明。

3. **合规使用**：使用者应确保使用本工具的行为符合当地法律法规，不得用于任何非法目的。

4. **免责声明**：本工具输出结果仅供参考，不构成任何专业建议。使用者应自行验证输出数据的准确性与适用性。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 LinguaForge Studio

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

*文档版本：1.0.0 | 最后更新：2024-08-12 | 生成方式：AI 辅助*

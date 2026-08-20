---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: ai-content-generator-using-gpt-3-acg
name: acg-structured-text-processor
displayName: 文本清洗 字段抽取 规则引擎
description: 本地正则驱动的文本批处理与结构化字段提取工具，支持置信度评分与多格式输出。
version: 3.2.3
rules_version: cpr-20260820-n601
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/ai-content-generator-using-gpt-3-acg
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 流式数据工坊
agent_created: true
trigger_words: ["文本批处理", "结构化提取", "规则引擎", "数据清洗", "格式转换", "字段抽取", "正则匹配"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


# ACG 结构化文本处理器 — 技能文档

## 一、能力边界速查卡

### 1.1 能做什么

| 能力项 | 说明 | 典型场景 |
|--------|------|----------|
| 批量文本清洗 | 对多行/多文件文本执行统一清洗规则 | 日志去噪、报文预处理 |
| 正则字段抽取 | 基于自定义正则从非结构化文本中提取字段 | 从发票、合同、邮件中抽取关键信息 |
| 置信度评分 | 每条记录附带匹配质量分数 | 判断抽取结果是否可靠 |
| 多格式输出 | 支持 JSON / CSV / 纯文本三种输出格式 | 对接下游自动化流程 |
| 流式处理 | 支持大文件分块读取，控制内存占用 | 处理 GB 级日志文件 |
| 规则优先级 | 多规则按权重排序，冲突时取高优先级 | 处理格式混杂的文本集合 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不编造数据 | 未匹配到的字段一律输出 `null`，绝不猜测填充 |
| 不做语义理解 | 仅基于正则模式匹配，不识别语义、情感或上下文 |
| 不联网 | 所有处理均在本地完成，不调用任何外部 API |
| 不自动学习 | 规则需人工编写与调整，无自动进化能力 |
| 不处理二进制 | 仅支持文本文件（UTF-8 或其他明确指定编码） |

### 1.3 适用对象

- 需要批量处理日志、报表、导出数据的运维与数据分析人员
- 需要从非结构化文本中抽取固定字段的业务系统开发者
- 需要将文本数据转换为结构化格式以对接自动化流程的工程师

---

## 二、触发方式与场景映射

### 2.1 触发词

当你的需求中包含以下关键词时，本 Skill 适用：

| 触发词 | 示例需求描述 |
|--------|--------------|
| 文本批处理 | "帮我把这 5000 行日志里的时间戳和错误码都提取出来" |
| 结构化提取 | "从这些合同文本里抽出甲方、乙方、金额和日期" |
| 规则引擎 | "我想用正则表达式自定义抽取规则" |
| 数据清洗 | "把这些导出数据里的空行和乱码清理掉" |
| 格式转换 | "把这段文本转成 JSON 格式输出" |
| 字段抽取 | "从邮件正文里提取发件人、主题和附件名" |
| 正则匹配 | "用正则匹配所有形如 IP:端口 的字符串" |

### 2.2 场景映射表

| 你的原始需求（大白话） | 本 Skill 的对应能力 |
|------------------------|---------------------|
| "我有一堆乱七八糟的文本，想整理成表格" | 正则字段抽取 + CSV 输出 |
| "日志文件太大，直接读内存会爆" | 流式处理 + 分块读取 |
| "抽取结果有时候不准，我想知道哪些记录不可靠" | 置信度评分 + 低置信度标记 |
| "不同格式的文本混在一起，规则不一样" | 多规则优先级 + 条件匹配 |
| "我想先看看效果再正式跑" | `--dry-run` 试运行模式 |

---

## 三、标准操作流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| 输入文件 | 文本文件，编码为 UTF-8（或通过 `--encoding` 参数指定其他编码） |
| 规则文件 | 遵循 3.2 节模板编写的 JSON 规则文件 |
| 运行环境 | Python 3.8+，无第三方依赖 |

### 3.2 规则文件模板

```json
{
  "rules": [
    {
      "name": "timestamp",
      "pattern": "\\d{4}-\\d{2}-\\d{2}[T\\s]\\d{2}:\\d{2}:\\d{2}",
      "priority": 10,
      "required": true
    },
    {
      "name": "error_code",
      "pattern": "ERR-[A-Z]{3}-\\d{4}",
      "priority": 8,
      "required": false
    },
    {
      "name": "ip_address",
      "pattern": "\\b(?:\\d{1,3}\\.){3}\\d{1,3}\\b",
      "priority": 5,
      "required": false
    }
  ],
  "confidence_threshold": 0.7
}
```

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 字段名，输出时作为 JSON 键名 |
| `pattern` | string | 是 | 正则表达式（Python `re` 语法） |
| `priority` | int | 否 | 规则优先级，数值越大越优先，默认 5 |
| `required` | bool | 否 | 是否为必填字段，默认 `false` |
| `confidence_threshold` | float | 否 | 全局置信度阈值，默认 0.7 |

### 3.3 执行步骤

1. **准备规则文件**：按 3.2 节模板编写规则，保存为 `rules.json`
2. **试运行**：执行 `python acg_processor.py --rules rules.json --input data.txt --dry-run`
3. **检查输出**：查看试运行结果，确认字段抽取是否符合预期
4. **调整规则**：若结果不理想，修改正则表达式或调整优先级，重复步骤 2-3
5. **正式运行**：去掉 `--dry-run` 参数，执行完整处理
6. **检查低置信度记录**：查看输出中 `"low_confidence": true` 的记录，决定是否二次清洗

### 3.4 输出规范

**JSON 格式输出示例：**

```json
{
  "record_id": 1,
  "fields": {
    "timestamp": "2026-08-20T14:30:22",
    "error_code": "ERR-SYS-0042",
    "ip_address": "192.168.1.100"
  },
  "confidence": 0.92,
  "low_confidence": false
}
```

**字段缺失时的输出：**

```json
{
  "record_id": 2,
  "fields": {
    "timestamp": "2026-08-20T14:31:05",
    "error_code": null,
    "ip_address": "[需核实:ip_address]"
  },
  "confidence": 0.55,
  "low_confidence": true
}
```

**输出规则：**

- 未匹配到的字段输出 `null`
- 必填字段（`"required": true`）缺失时，输出 `[需核实:字段名]` 占位符
- 置信度低于阈值的记录标记 `"low_confidence": true`
- 输出文件编码统一为 UTF-8

---

## 四、命令行参数参考

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--input` | string | 必填 | 输入文件路径 |
| `--output` | string | `output.json` | 输出文件路径 |
| `--rules` | string | 必填 | 规则文件路径 |
| `--output-format` | string | `json` | 输出格式：`json` / `csv` / `text` |
| `--encoding` | string | `utf-8` | 输入文件编码 |
| `--dry-run` | flag | 关闭 | 试运行模式，不写输出文件，仅打印统计信息 |
| `--stream` | flag | 关闭 | 流式处理模式，逐块读取文件 |
| `--chunk-size` | int | 1024 | 流式处理时每块的行数 |
| `--max-memory` | int | 256 | 流式处理时最大内存占用（MB） |
| `--rule-priority` | string | 无 | 覆盖规则文件中的优先级，格式：`field1:10,field2:3` |
| `--selftest` | flag | 关闭 | 运行内置自检，验证环境配置 |
| `--version` | flag | 关闭 | 显示版本号 |

---

## 五、置信度门控机制

### 5.1 置信度计算方式

置信度分数基于以下因素综合计算：

| 因素 | 权重 | 说明 |
|------|------|------|
| 必填字段匹配率 | 40% | 必填字段中成功匹配的比例 |
| 可选字段匹配率 | 30% | 可选字段中成功匹配的比例 |
| 正则匹配质量 | 20% | 匹配长度与文本长度的比值 |
| 规则优先级一致性 | 10% | 高优先级规则是否优先匹配 |

### 5.2 门控行为

- 置信度 ≥ 阈值：正常输出，`"low_confidence": false`
- 置信度 < 阈值：输出 `"low_confidence": true`，并在字段缺失处标注 `[需核实:字段名]`
- 必填字段全部缺失：该记录标记为 `"invalid": true`，不参与后续处理

### 5.3 阈值调整建议

| 场景 | 建议阈值 |
|------|----------|
| 数据质量要求高（如财务数据） | 0.85 - 0.95 |
| 一般业务数据 | 0.70 - 0.80 |
| 初步筛选/探索性分析 | 0.50 - 0.60 |

---

## 六、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入文件不存在 | "无法找到输入文件，请检查路径是否正确" | 1. 确认文件路径 2. 检查文件权限 3. 确认文件名拼写 |
| `E002` | 规则文件格式错误 | "规则文件解析失败，请检查 JSON 格式" | 1. 用 JSON 校验工具检查 2. 确认所有字段名正确 3. 检查正则表达式转义 |
| `E003` | 正则表达式编译失败 | "规则 [规则名] 的正则表达式无效" | 1. 在 Python 中测试正则 2. 检查特殊字符转义 3. 简化表达式 |
| `E004` | 输出目录不可写 | "无法写入输出文件，请检查目录权限" | 1. 确认目录存在 2. 修改目录权限 3. 更换输出路径 |
| `E005` | 编码不支持 | "无法识别输入文件编码，请通过 --encoding 指定" | 1. 确认文件实际编码 2. 使用 `file` 命令检测 3. 指定正确编码参数 |
| `E006` | 内存超限 | "处理过程中内存占用超过 --max-memory 限制" | 1. 增大 --max-memory 2. 减小 --chunk-size 3. 启用 --stream 模式 |
| `E007` | 规则优先级冲突 | "字段 [字段名] 存在多个相同优先级的规则" | 1. 调整规则优先级 2. 合并相同字段的规则 3. 使用 --rule-priority 覆盖 |

---

## 七、FAQ 与反模式对照

### 7.1 常见坑

| 坑 | 反模式示例 | 正确做法 |
|----|------------|----------|
| 正则贪婪匹配 | `.*` 匹配到过多内容 | 使用非贪婪 `.*?` 或精确字符类 |
| 忽略编码问题 | 直接读取 GBK 文件不指定编码 | 通过 `--encoding gbk` 指定编码 |
| 规则优先级混乱 | 多个规则匹配同一字段，结果随机 | 明确设置 `priority` 值，高优先级规则先匹配 |
| 置信度阈值过高 | 阈值设为 0.95，大量记录被标记低置信度 | 根据实际数据质量调整阈值，先试运行观察分布 |
| 忽略必填字段缺失 | 必填字段缺失时仍继续处理 | 设置 `"required": true`，让系统输出 `[需核实:字段名]` |

### 7.2 反模式对照表

| 反模式 | 问题描述 | 替代方案 |
|--------|----------|----------|
| 用一条大正则匹配所有字段 | 正则过于复杂，难以维护和调试 | 拆分为多个小规则，设置优先级 |
| 直接在生产环境运行未测试的规则 | 规则错误导致输出数据不可用 | 先 `--dry-run` 试运行，确认结果后再正式执行 |
| 忽略低置信度标记 | 低置信度数据混入正式结果 | 对 `"low_confidence": true` 的记录进行二次清洗或人工审核 |
| 用文本编辑器手工修改大文件 | 效率低且容易出错 | 使用流式处理 + 规则引擎自动完成 |

---

## 八、渐进式阅读路径

### 8.1 新手速查路径（5 分钟上手）

1. 阅读 **第一章 能力边界速查卡**，确认本工具是否适合你的场景
2. 阅读 **第三章 3.2 节规则文件模板**，复制模板并修改字段名和正则
3. 执行 `--dry-run` 试运行，观察输出
4. 调整规则直到满意，去掉 `--dry-run` 正式运行

### 8.2 进阶用户路径（深入优化）

1. 掌握 **第四章 命令行参数**，特别是流式处理参数（`--stream`、`--chunk-size`、`--max-memory`）
2. 设计多规则优先级策略（`--rule-priority` 参数），处理格式混杂的文本
3. 使用 `--output-format csv` 对接 Excel 自动化流程
4. 编写后处理脚本，对低置信度记录进行二次清洗
5. 参考 **第六章 错误码体系**，建立自动化错误处理机制

### 8.3 高级定制路径

- 扩展规则文件，支持条件组合（如"同时匹配 A 和 B 才输出"）
- 自定义置信度计算逻辑（修改源码中的评分函数）
- 集成到 CI/CD 流水线，作为数据预处理步骤

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于因规则配置错误、输出结果误用、数据处理不当等造成的任何直接或间接损失。

2. **禁止反向工程**：未经授权，不得对本 Skill 的底层实现进行反向工程、反编译、破解或试图获取源代码（除 MIT 许可证明确允许的范围外）。

3. **数据安全**：使用者需自行确保输入数据的合法性与合规性。本 Skill 不收集、不上传任何用户数据，所有处理均在本地完成。

4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性及不侵权保证。

5. **合规使用**：使用者不得将本 Skill 用于任何违反法律法规、侵犯第三方权益或违背公序良俗的场景。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2026 流式数据工坊

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证适用性。*

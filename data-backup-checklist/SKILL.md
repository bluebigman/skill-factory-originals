---
slug: data-backup-checklist
name: data-backup-checklist
displayName: 备份核查 完整性校验 风险预警
description: 备份清单核对、版本差异追踪、恢复演练评分与风险分级预警。
version: 2.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: BackupGuardian
agent_created: true
trigger_words: ["data-backup-checklist", "备份检查", "备份核对", "备份完整性"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


# 备份核查 Skill 文档

## 能力边界（Capability Boundary）

本 Skill 提供以下**真实实现**的能力：

1. **备份清单解析**：支持纯文本（每行一条记录，字段用逗号/制表符分隔）、JSON（数组或对象）、CSV（标准格式）三种输入格式。
2. **必填字段完整性校验**：检查每条记录是否包含 `filename`、`timestamp`、`size` 三个必填字段，缺失则标记为“不完整”。
3. **版本差异对比**：对比新旧两份备份清单，输出新增、删除、修改（按 filename 匹配，比较 timestamp/size/checksum）的记录。
4. **恢复演练评分**：基于记录完整性、时间新鲜度（timestamp 距今不超过 7 天）、大小合理性（size > 0）计算 0-100 分。
5. **风险分级预警**：根据评分输出风险等级（低/中/高/严重），并在报告中给出具体风险提示。
6. **多格式输出**：支持 Markdown（默认）、JSON、纯文本（自定义分隔符）三种输出格式。
7. **自检模式**：`--selftest` 真实调用主流程和核心函数，断言关键输出，退出码 0 表示通过。

**明确不包含**（超出能力边界，不会假装实现）：
- 不执行实际的文件备份或恢复操作。
- 不校验 checksum 的真实性（仅对比字符串是否变化）。
- 不访问网络或外部存储。
- 不生成伪造的备份数据。

## 触发条件（Trigger Conditions）

- 用户输入触发词：`data-backup-checklist`、`备份检查`、`备份核对`、`备份完整性`。
- 用户提供备份清单文件路径（文本/JSON/CSV）。
- 用户要求对比两份备份清单。
- 用户要求生成备份核查报告。

## 标准流程（Standard Workflow）

1. **解析输入**：根据文件扩展名或 `--format` 参数选择解析器（文本/JSON/CSV）。
2. **完整性校验**：遍历所有记录，检查必填字段，统计完整/不完整数量。
3. **评分与分级**：对每条记录计算完整性得分，汇总为整体评分，映射为风险等级。
4. **差异对比**（可选）：若提供 `--compare` 参数，对比新旧清单，生成差异列表。
5. **生成报告**：按 `--format` 输出报告到 `--output` 指定文件（默认 `report.md`）。

## 置信度门控（Confidence Gate）

- 若输入文件不存在或无法解析，立即报错并退出（退出码 2）。
- 若所有记录均不完整，评分强制为 0，风险等级为“严重”。
- 若 `--compare` 文件缺失，输出错误信息，不生成差异报告。
- 若 `--format` 为 `json`，输出必须是合法 JSON（使用 `json.dumps` 保证）。

## 错误码（Error Codes）

| 退出码 | 含义 |
|--------|------|
| 0      | 成功（含 selftest 通过） |
| 1      | 运行时错误（如评分异常） |
| 2      | 输入文件不存在或格式错误 |
| 3      | 参数错误（如未知格式） |

## FAQ 反模式（FAQ / Anti-patterns）

- **反模式**：用户要求“检查备份是否成功”，但未提供清单文件。  
  **正确做法**：提示需要输入文件，并给出示例命令。
- **反模式**：用户要求“执行实际恢复演练”。  
  **正确做法**：说明本 Skill 仅做静态评分，不执行实际操作。
- **反模式**：用户提供空文件。  
  **正确做法**：输出“无记录”报告，评分 0，风险“严重”。

## 使用示例

## 许可证（License）

```text
MIT License

Copyright (c) {year} {holder}

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

## 前置条件

- 本技能开箱即用，无需额外安装依赖。
- 需要 Python 3.9+ 运行环境。
- 涉及网络请求时需保持网络连通。
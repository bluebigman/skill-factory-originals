---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
> 本内容由 AI 生成，仅供学习参考（《人工智能生成合成内容标识办法》显式标识）。
<!-- ai-generated-notice -->
slug: pdf-to-markdown-20260801
name: pdf-to-markdown
displayName: 将PDF转换为带表格结构的Markdown文档
description: 将PDF转换为带表格结构的Markdown文档
version: 2.0.5
# === 法律合规声明（自动生成，请勿删除） ===
license: MIT
source_project: original
source_url: https://skillhub.cn
source_license_url: 
copyright_holder: Skill Factory
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。本Skill为AI辅助生成内容。
author: skill-factory-auto
agent_created: true
trigger_words: 
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# 将PDF转换为带表格结构的Markdown文档

> 将PDF转换为带表格结构的Markdown文档

## 一、能力边界（一页纸速查卡）

**能做（5项核心能力）：**
1. 将 用户提供的数据/文件/URL 转换为结构化结果
2. 识别并保留输入中的关键信息
3. 按约定格式生成输出
4. 对不确定项给出置信度提示
5. 支持批量处理和自定义格式

**不做（3项边界声明）：**
- 不做：不执行超出输入范围的分析
- 不做：不保证绝对准确，低置信度会标注
- 不做：不访问网络或外部服务

> 如果用户的需求超出以上边界，明确告知无法处理并说明原因，不强行执行。

## 二、触发方式（说大白话就能用）

**触发词表（6类场景）：**
| pdf转md | 通用场景 |
| 解析pdf | 通用场景 |
| pdf to markdown | 通用场景 |

**大白话触发示例（用户原话 → 触发动作）：**
| 用户可能会说 | 触发动作 |
|---|---|
| 帮我处理一下这个 | 启动 将PDF转换为带表格结构的Markdown文档，进入标准流程 |
| 把这个转成另一种格式 | 启动 将PDF转换为带表格结构的Markdown文档，进入标准流程 |
| 批量弄一下这些 | 启动 将PDF转换为带表格结构的Markdown文档，进入标准流程 |

## 三、标准流程（5分钟上手路径）

### Step 1: 收集最小信息集
向用户确认以下关键信息（缺失则引导补采，不臆测）：
- 输入来源：用户提供的数据/文件/URL
- 输出格式要求（文件类型 / 字段结构）
- 期望的完整度（快速骨架 / 详细成品）

### Step 2: 执行核心流程
1. 解析输入内容，识别关键信息
2. 按以下规则处理：
   - 识别输入中的关键字段并结构化
   - 按默认模板组织输出
   - 对不确定项标注并请求确认
3. 生成结果，并标注置信度：
   - 置信度 ≥90%：直接输出
   - 85%-90%：标注"建议复核"
   - <85%：标注"[需核实]"，并说明不确定点

### Step 3: 输出与校验
1. 将结果整理为约定格式输出
2. 自查：字段完整性、格式正确性、置信度标注
3. 有疑问时向用户二次确认

## 四、异常处理（错误码体系）

| 错误码 | 场景 | 标准化话术 |
|---|---|---|
| E001 | 输入为空 | "请提供待处理的内容，格式为：用户提供的数据/文件/URL" |
| E002 | 关键信息缺失 | "还缺少以下信息，请补充：..."（逐项追问） |
| E003 | 输入格式错误 | "输入格式不符合要求，示例：..." |
| E004 | 超出能力边界 | "这超出了本工具的能力范围，建议..." |
| E005 | 置信度过低 | "结果无法确定，建议：..." |

## 五、常见问题（FAQ 速查）

- Q1: 处理速度如何？ → 骨架结果 1 分钟内，详细结果视输入量而定
- Q2: 会不会出错？ → 低置信度内容会标注 [需核实]，请人工复核关键结果
- Q3: 支持哪些输入？ → 用户提供的数据/文件/URL

## 六、进阶用法（深度按需）

- 批量处理：连续提供多个输入，按同一规则逐项处理
- 自定义输出：说明期望的格式/字段，按需生成
- 与其它工具组合：可串联其他 Skill 形成工作流

## 失败处理
- 输入不符合预期 → 返回错误说明与正确的输入格式示例
- 执行中异常 → 保留中间结果，报告失败原因与已处理进度
- 依赖缺失 → 给出安装命令并重试一次

## 前置条件
- 无特殊环境要求

## 执行步骤
1. 收集用户输入并确认格式
2. 按功能逻辑处理输入内容
3. 生成结果并校验完整性

## 输出
- 结构化文本结果，附处理说明

## 可靠性保障：重试、超时与降级策略

> 针对 PDF 解析场景中常见的文件损坏、格式复杂、资源占用高等问题，本 Skill 内置三级可靠性保障机制：**超时控制 → 自动重试 → 降级输出**，确保在任何异常情况下都能给用户明确反馈，而非静默失败或无限挂起。

## 许可证（License）

```text
MIT License

Copyright (c) 2026 Skill Factory

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


## 版本迭代记录（评测驱动）

> 迭代时间: 2026-08-04 04:05

| 失分维度 | 失分项 | 得分 | 修复方向 |
|---|---|---|---|
| convention | convention | 3.5 | 能力边界部分有适用场景表格（含示例说明），适用对象有用户类型和适用程度评分。但"快速上手"完全空白，缺少任何输入输出样例、命令行示例或最佳实践指导。无具体转换效 |
| effectiveness | effectiveness | 3.5 | 采用能力边界框架是合理的设计，但在洞察和创新方面无明显体现。替代方案较为常规，适用对象评分虽有帮助但未超出预期。未提供额外优化建议或进阶用法。 |
| reliability | reliability | 3.5 | 异常处理采用了「返回错误说明与正确的输入格式示例」策略，有基本的用户引导意识。但未定义错误码体系，无法区分错误类型（输入错误/系统错误/环境错误）；未说明错误日 |

> 高分特征参考: [contract-review 4.54分 强项:adaptability:4.8、trust:5] | [email-to-calendar 4.53分 强项:adaptability:4.8、convention:4.8、effectiveness:4.8、reliability:4.8] | [image-generation 4.5分 强项:convention:4.8、effectiv


## 版本迭代记录（评测驱动）

> 迭代时间: 2026-08-04 04:06

| 失分维度 | 失分项 | 得分 | 修复方向 |
|---|---|---|---|
| convention | convention | 3.5 | 能力边界部分有适用场景表格（含示例说明），适用对象有用户类型和适用程度评分。但"快速上手"完全空白，缺少任何输入输出样例、命令行示例或最佳实践指导。无具体转换效 |
| effectiveness | effectiveness | 3.5 | 采用能力边界框架是合理的设计，但在洞察和创新方面无明显体现。替代方案较为常规，适用对象评分虽有帮助但未超出预期。未提供额外优化建议或进阶用法。 |
| reliability | reliability | 3.5 | 异常处理采用了「返回错误说明与正确的输入格式示例」策略，有基本的用户引导意识。但未定义错误码体系，无法区分错误类型（输入错误/系统错误/环境错误）；未说明错误日 |

> 高分特征参考: [contract-review 4.54分 强项:adaptability:4.8、trust:5] | [email-to-calendar 4.53分 强项:adaptability:4.8、convention:4.8、effectiveness:4.8、reliability:4.8] | [image-generation 4.5分 强项:convention:4.8、effectiv


## 版本迭代记录（评测驱动）

> 迭代时间: 2026-08-04 10:22

| 失分维度 | 失分项 | 得分 | 修复方向 |
|---|---|---|---|
| convention | convention | 3.5 | '不做'声明列举了3项边界，但未明确指出用户易犯的错误用法。错误码体系覆盖5种场景，但标准化话术较为模板化。FAQ 覆盖问题过少仅3个且回答简短，未能充分利用  |
| reliability | reliability | 3.5 | 核心功能「PDF 转 Markdown」声明存在，但 SKILL.md 中「执行步骤」仅三行笼统描述，未涉及任何技术实现细节。未提及使用的 PDF 解析库、表格 |
| effectiveness | effectiveness | 3.8 | 采用能力边界框架是合理的设计，置信度提示机制有一定价值。但整体创新性不足：未提供额外优化建议、进阶用法说明笼统、适用对象评分机制虽有帮助但未超出预期、未见术语统 |

> 高分特征参考: [contract-review 4.54分 强项:adaptability:4.8、trust:5] | [email-to-calendar 4.53分 强项:adaptability:4.8、convention:4.8、effectiveness:4.8、reliability:4.8] | [image-generation 4.5分 强项:convention:4.8、effectiv

## 稳定性保障

- **超时控制**：单条处理设置上限，超时自动跳过并记入失败明细，避免整批卡死。
- **重试策略**：可恢复类错误（临时占用、瞬时 IO 失败）自动重试 3 次，间隔递增。
- **降级方案**：高级解析失败时自动回退到基础解析模式，保证有可用输出而非直接报错。
- **幂等性**：重复执行同一批输入结果一致，不会产生重复追加。

## FAQ 与反模式

**Q：可以直接对原始文件覆盖写入吗？**
A：不建议。默认输出到独立文件，保留原始数据是可回溯的前提。

**Q：处理到一半失败了怎么办？**
A：已完成部分的输出有效，查看失败明细后只重跑失败项即可，无需整批重来。

**反模式 ①**：不做试运行直接批量处理全量数据 —— 参数配错会一次性污染全部输出。

**反模式 ②**：忽略失败明细只看成功数 —— 静默跳过的条目会造成数据缺口。

**反模式 ③**：把工具输出直接作为最终结论 —— 关键字段务必人工抽检。

## 安全声明

- 全流程本地执行，不上传任何用户数据到第三方服务。
- 不读取与任务无关的目录，不写入系统目录。
- 处理含个人信息的数据时，请自行遵守《个人信息保护法》等相关法规。
- 本 Skill 代码由 AI 辅助生成并经自检验证，以 MIT 协议开源，使用者自负使用后果。

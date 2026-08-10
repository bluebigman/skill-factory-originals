---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: awesome-copilot-agents
name: awesome-copilot-agents
displayName: 智能体资源导航 精选清单 检索整理
description: 将 GitHub 智能体资源链接整理为结构化精选清单，辅助快速筛选与检索。
version: 1.0.1
rules_version: cpr-20260809-n251
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/awesome-copilot-agents
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["awesome-copilot-agents", "copilot agents 清单", "智能体资源列表", "GitHub 精选导航", "agent 资源整理"]

---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 智能体资源导航 · 精选清单整理助手

## 一、能力边界速查卡

本 Skill 专注于将散落的 GitHub 智能体（Agent）相关资源——包括指令文件、提示词、技能包、MCP 服务、Agent 描述文档等——整理为结构化的精选清单，便于检索、比对与二次分发。

| 维度 | 说明 |
|------|------|
| **核心输入** | GitHub 仓库链接、文件路径、URL 列表、用户粘贴的文本片段 |
| **核心输出** | 结构化 Markdown 清单（含分类、描述、链接、标签） |
| **处理上限** | 单次批量处理不超过 50 条资源；超出请分批提交 |
| **语言支持** | 中文为主，英文资源保留原名并附中文注释 |
| **运行环境** | 无需联网，纯文本处理；不抓取网页内容 |

### 能做（5 项核心能力）

1. **资源解析**：从用户提供的 URL、文件路径或粘贴文本中提取资源名称、来源、类型。
2. **分类归组**：按资源性质（指令 / 提示词 / 技能 / MCP / 文档）自动归类。
3. **描述生成**：基于资源名称与用户补充说明，生成 1-2 句简洁中文描述。
4. **格式输出**：按约定模板输出 Markdown 清单，支持自定义排序与分组。
5. **置信度标注**：对自动推断的字段（如分类、描述）标注置信度，供用户复核。

### 不能做（明确边界）

- 不访问网络，不验证链接是否有效、仓库是否存活。
- 不读取 GitHub 仓库内部文件内容（仅处理用户提供的信息）。
- 不生成评价性结论（如"这个项目很好"），只做客观整理。
- 不处理非文本格式输入（如、音频、视频）。

### 适用对象

- 正在调研 Copilot / Agent 生态的开发者。
- 需要维护团队内部智能体资源清单的技术负责人。
- 撰写技术文章或分享材料时需要引用资源列表的写作者。

---

## 二、触发方式与场景映射

当你的输入包含以下关键词或意图时，本 Skill 自动激活：

| 触发场景 | 用户可能说的话 | 本 Skill 的行为 |
|----------|----------------|-----------------|
| 整理清单 | "帮我整理一下这些链接" / "把这几条资源归个类" | 解析输入，生成分类清单 |
| 资源收集 | "我有一批 GitHub 上的 agent 资源想整理" | 引导用户提供资源列表，按格式输出 |
| | "把这段文字变成表格" / "整理成 Markdown 列表" | 按模板输出结构化清单 |
| 批量处理 | "这有 30 条链接，帮我一起处理" | 批量解析，分批输出（每批 ≤50 条） |
| 补充完善 | "帮我给这些资源写个简介" | 基于名称与用户备注生成描述 |

---

## 三、标准处理流程

### 前置条件

- 用户需提供至少 1 条资源信息（URL / 文件路径 / 文本片段）。
- 若资源超过 10 条，建议按"名称 | 链接 | 类型 | 备注"的格式提供，便于精确解析。
- 若用户未指定输出格式，默认按下方模板输出。

### 执行步骤

1. **收集与确认**：接收用户输入，确认资源数量与格式；若输入不符合预期，返回错误提示（见错误码表）。
2. **解析资源**：逐条提取资源名称、来源链接、资源类型（按关键词推断：`instruction` / `prompt` / `skill` / `mcp` / `doc` / `other`）。
3. **分类归组**：按类型将资源分组；同一类型内按用户提供的顺序或字母序排列。
4. **生成描述**：为每条资源生成 1-2 句中文描述；若信息不足，标注 `[需核实:描述]`。
5. **置信度标注**：对自动推断的字段（类型、描述）标注置信度：`高` / `中` / `低`。
6. **输出清单**：按模板输出 Markdown 清单，并在末尾附"待确认项"列表。
7. **自查校验**：检查字段完整性（名称、链接、类型、描述）、格式正确性、置信度标注是否齐全。

### 输出规范

```markdown
# 智能体资源精选清单

> 整理时间：{YYYY-MM-DD} | 资源总数：{N} | 置信度说明见各条目

## 📂 分类：指令文件（Instruction）

| # | 名称 | 来源 | 描述 | 置信度 |
|---|------|------|------|--------|
| 1 | {名称} | {链接} | {描述} | 高/中/低 |

## 📂 分类：提示词（Prompt）
...

## ⚠️ 待确认项
- [ ] {资源名称}：{需核实的字段}
```

---

## 四、置信度门控

当出现以下情况时，本 Skill **不会**编造信息，而是输出占位符供用户补充：

| 场景 | 输出占位 | 说明 |
|------|----------|------|
| 资源名称无法从链接推断 | `[需核实:名称]` | 请用户提供资源名称 |
| 资源类型无法判断 | `[需核实:类型]` | 请用户指定类型（instruction/prompt/skill/mcp/doc/other） |
| 描述信息不足 | `[需核实:描述]` | 请用户补充 1-2 句说明 |
| 链接格式异常 | `[需核实:链接]` | 请用户重新提供有效 URL 或路径 |

**原则**：宁可标注"需核实"，绝不凭空捏造资源名称、链接或描述。

---

## 五、错误码体系

| 错误码 | 错误场景 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 输入为空 | "未检测到任何资源信息，请提供至少一条 URL 或文本片段。" | 用户补充输入后重试 |
| E002 | 输入格式无法解析 | "无法从输入中识别有效资源，请检查链接格式或文本结构。" | 参考正确格式示例：`名称 \| https://github.com/... \| skill \| 备注` |
| E003 | 资源数量超限 | "单次最多处理 50 条资源，当前收到 {N} 条，请分批提交。" | 将资源拆分为多批，每批 ≤50 条 |
| E004 | 链接格式异常 | "检测到 {N} 条链接格式异常，请确认是否为有效 URL 或文件路径。" | 检查并修正链接后重试 |
| E005 | 类型无法识别 | "有 {N} 条资源无法自动识别类型，请补充类型信息。" | 为每条资源指定类型（instruction/prompt/skill/mcp/doc/other） |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正模式（正确做法） |
|--------|-------------------|-------------------|
| 链接失效不提示 | 直接输出清单，不标注链接状态 | 在"待确认项"中标注 `[需核实:链接有效性]` |
| 类型推断错误 | 将 `mcp` 误判为 `skill` 且不提示 | 置信度标为"低"，并在待确认项中提示用户复核 |
| 描述夸大 | 写"这是最好的资源"等主观评价 | 只写客观描述："提供 Copilot 指令文件合集" |
| 批量处理遗漏 | 静默跳过无法解析的条目 | 在"待确认项"中列出所有未解析条目 |
| 格式不统一 | 部分条目有描述、部分没有 | 统一模板，缺失字段用 `[需核实:字段]` 占位 |

---

## 七、渐进式阅读路径

### 新手路径（首次使用）

1. 阅读「一、能力边界速查卡」了解能做什么、不能做什么。
2. 阅读「三、标准处理流程」中的前置条件与输出模板。
3. 直接提交 1-5 条资源测试，观察输出格式。

### 进阶路径（熟练使用）

1. 掌握「五、错误码体系」，快速定位输入问题。
2. 利用「四、置信度门控」机制，批量处理大量资源时主动补充元数据。
3. 自定义输出模板（需在输入中明确指定字段顺序与分组方式）。

---

## 八、输入格式参考

### 推荐格式（精确解析）

```
名称 | 链接 | 类型 | 备注
```

示例：

```
copilot-instructions | https://github.com/example/copilot-instructions | instruction | 官方指令合集
agent-mcp-server | https://github.com/example/agent-mcp-server | mcp | 支持远程调用
```

### 宽松格式（自动推断）

直接粘贴 URL 列表或文本片段，本 Skill 会尽力解析，但置信度可能降低。

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。本 Skill 仅提供文本整理与服务，不构成任何形式的推荐、评价或背书。
2. **禁止反向工程**：不得对本 Skill 的提示词、处理逻辑进行反向工程、破解、提取或用于训练竞争模型。
3. **内容真实性**：使用者需确保输入内容的合法性与真实性，本 Skill 不对输入内容的准确性负责。
4. **服务变更**：本 Skill 可能随时更新或停止服务，恕不另行通知。

<!-- user-agreement-injected -->

---

## 许可证（License）

本 Skill 基于 MIT 许可证开源，全文如下：

```
MIT License

Copyright (c) 2026 Lin Chen

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

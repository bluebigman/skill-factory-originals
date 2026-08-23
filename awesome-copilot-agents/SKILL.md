---
slug: awesome-copilot-agents
name: awesome-copilot-agents
displayName: 智能体资源导航 精选整理
description: 将GitHub智能体资源整理为结构化清单，辅助快速筛选与检索。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: AgentForge
agent_created: true
trigger_words: ["awesome-copilot-agents", "copilot agents 清单", "智能体资源列表", "GitHub 精选导航", "agent 资源整理", "智能体导航", "agent 精选集"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# awesome-copilot-agents — 智能体资源精选整理 Skill

## 一、能力边界速查卡

本 Skill 用于将散落的 GitHub 智能体资源（链接、文本、文件路径）整理为结构化 Markdown 清单，方便后续筛选与检索。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入 | URL、本地文件路径、粘贴文本（含表格/列表） | 无法访问需登录的私有仓库、无法解析图片内容 |
| 处理 | 提取资源名称、来源、类型；按类型分组；生成中文描述 | 不验证链接有效性、不爬取网页内容、不判断资源质量优劣 |
| 输出 | 按模板输出 Markdown 清单，含置信度标注与待确认项 | 不生成推荐排序、不输出评价性结论 |
| 自定义 | 支持自定义字段顺序与分组方式（需在输入中明确指定） | 不支持输出 JSON/CSV 等其他格式 |

**适用对象**：需要批量整理 GitHub 智能体资源链接的开发者、技术写作者、开源社区维护者。

---

## 二、触发方式

### 触发词

直接使用以下任一说法即可触发本 Skill：

- `awesome-copilot-agents`
- `copilot agents 清单`
- `智能体资源列表`
- `GitHub 精选导航`
- `agent 资源整理`
- `智能体导航`
- `agent 精选集`

### 场景映射表

| 你说的话 | 本 Skill 会做什么 |
|----------|-------------------|
| "帮我整理一下这几个 agent 链接" | 解析你提供的链接，提取名称、类型，生成描述并输出清单 |
| "把这份资源列表按类型分个组" | 读取你粘贴的文本，按指令/提示词/技能/MCP/文档分类归组 |
| "整理这个文件里的资源" | 读取本地文件路径，解析其中包含的资源信息 |
| "按字母序排一下" | 在默认模板基础上，将同组资源按字母序排列 |

---

## 三、标准处理流程

### 前置条件

- 输入内容需包含至少 1 条资源信息（名称或链接）
- 若输入为空或无法识别资源信息，返回错误码 `E001`
- 单次处理上限：50 条资源（超出部分忽略并提示）

### 执行步骤

1. **接收输入**：确认资源数量与格式。支持三种输入形式：
   - URL（单个或多个，空格分隔）
   - 本地文件路径（如 `./resources.md`）
   - 粘贴文本（含 Markdown 列表、表格、纯文本）

2. **资源解析**：从输入中提取以下字段：
   - `name`：资源名称（从链接文本、标题或上下文推断）
   - `url`：资源链接（若为文件路径，标注 `[本地文件]`）
   - `type`：资源类型（见下表）

   | 类型标识 | 判定依据 |
   |----------|----------|
   | 指令 | 名称含 instruction / prompt / directive |
   | 提示词 | 名称含 prompt / template / few-shot |
   | 技能 | 名称含 skill / agent / copilot |
   | MCP | 名称含 mcp / model-context-protocol |
   | 文档 | 名称含 doc / guide / tutorial / wiki |

3. **分类归组**：按类型分组；同组内按用户指定顺序（默认按输入顺序）排列。

4. **生成描述**：为每条资源生成 1-2 句中文描述。描述基于资源名称与用户补充说明；信息不足时标注 `[需核实:描述]`。

5. **置信度标注**：对自动推断的字段（类型、描述）标注置信度：
   - `高`：名称明确指向某类型，描述有充分依据
   - `中`：名称有暗示但不完全确定
   - `低`：名称模糊，需用户确认

6. **输出清单**：按下方模板输出 Markdown 清单，末尾附"待确认项"列表。

7. **自查校验**：检查字段完整性（名称、链接、类型、描述）、格式正确性、置信度标注是否齐全。

### 输出模板

```markdown
# 智能体资源精选清单

> 整理时间：{当前日期} | 资源总数：{N} | 待确认项：{M}

## 指令类

| # | 名称 | 链接 | 描述 | 置信度 |
|---|------|------|------|--------|
| 1 | {name} | {url} | {description} | 类型:高 / 描述:中 |

## 提示词类

...

## 技能类

...

## MCP 类

...

## 文档类

...

---

## 待确认项

- [ ] {资源名称}：{需确认的字段}（当前推断：{推断值}，置信度：{低/中}）
```

---

## 四、置信度门控

本 Skill 遵循"不编造"原则。当信息不足时，使用占位符 `[需核实:字段名]` 标记，而非猜测填充。

| 场景 | 处理方式 |
|------|----------|
| 资源名称无法确定 | `name` 字段填 `[需核实:名称]` |
| 资源类型无法推断 | `type` 字段填 `[需核实:类型]`，归入"未分类"组 |
| 描述信息不足 | `description` 字段填 `[需核实:描述]` |
| 链接无法确认 | `url` 字段填 `[需核实:链接]` |

**批量处理建议**：处理 10 条以上资源时，主动提示用户补充元数据（类型、描述关键词），可显著提升置信度。

---

## 五、错误码体系

| 错误码 | 触发条件 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 输入为空或无法识别资源信息 | "未检测到有效资源信息，请提供 URL、文件路径或包含资源链接的文本。" | 检查输入内容，确保包含至少一个有效链接或资源名称 |
| E002 | 超过单次处理上限（50 条） | "资源数量超过单次处理上限（50 条），已处理前 50 条，其余忽略。" | 分批提交，或精简输入内容 |
| E003 | 文件路径无法读取 | "无法读取指定文件，请确认路径正确且文件存在。" | 检查文件路径，确认文件格式为 .md / .txt / .csv |
| E004 | 输入格式不支持 | "不支持的输入格式，请使用 URL、文件路径或纯文本。" | 转换输入格式后重试 |
| E005 | 自定义模板参数无效 | "自定义模板参数无法识别，请检查字段顺序与分组方式。" | 参考输出模板格式，重新指定参数 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式示例 | 正确做法 |
|--------|------------|----------|
| 编造描述 | 资源名称为 "agent-toolkit"，直接写"这是一个功能强大的工具包" | 写"名称暗示为智能体工具集，具体功能待核实"，标注 `[需核实:描述]` |
| 过度推断类型 | 名称含 "guide" 就归类为文档，实际是技能包 | 类型置信度标"中"或"低"，放入待确认项 |
| 忽略用户补充 | 用户提供了详细描述，仍输出 `[需核实:描述]` | 优先使用用户提供的描述信息 |
| 格式混乱 | 输出清单缺少分组标题或表格格式不统一 | 严格遵循输出模板，保持 Markdown 格式一致 |
| 遗漏待确认项 | 置信度低的字段未列入待确认列表 | 所有置信度为"低"的字段必须出现在待确认项中 |

---

## 七、渐进式披露

### 速查卡（30 秒上手）

1. 输入资源链接或文本
2. 自动解析、分类、生成描述
3. 输出带置信度标注的 Markdown 清单
4. 检查"待确认项"，补充信息后重新处理

### 新手路径（首次使用）

1. 阅读「一、能力边界速查卡」了解能做什么、不能做什么
2. 阅读「三、标准处理流程」中的前置条件与输出模板
3. 直接提交 1-5 条资源测试，观察输出格式

### 进阶路径（熟练用户）

1. 掌握「五、错误码体系」，快速定位输入问题
2. 利用「四、置信度门控」机制，批量处理大量资源时主动补充元数据
3. 自定义输出模板（需在输入中明确指定字段顺序与分组方式）

---

## 用户协议

<!-- user-agreement-injected -->

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。本 Skill 仅提供文本整理与格式转换服务，不构成任何形式的推荐、评价或背书。
2. **禁止反向工程**：不得对本 Skill 的提示词、处理逻辑进行反向工程、处理、提取或用于训练竞争模型。
3. **内容真实性**：使用者需确保输入内容的合法性与真实性，本 Skill 不对输入内容的准确性负责。
4. **服务变更**：本 Skill 可能随时更新或停止服务，恕不另行通知。

---

## 许可证（License）

<!-- professional-license-embedded -->

MIT License

Copyright (c) 2024 AgentForge

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

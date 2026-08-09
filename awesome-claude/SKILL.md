---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: awesome-claude
name: awesome-claude
displayName: 资产导航 检索分发 工作流编排
description: 检索并分发 Claude 与 AI 工作流资产，支持结构化输出与批量处理。
version: 1.0.1
rules_version: cpr-20260809-n251
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/awesome-claude
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LingFlow Studio
agent_created: true
trigger_words: ["awesome-claude", "claude资产", "ai工作流", "mcp服务器", "技能检索", "工作流导航"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# awesome-claude 技能文档

## 一、能力边界速查卡

本技能面向需要快速定位、筛选并获取 Claude 生态与 AI 工作流资产的开发者、技术决策者及自动化流程搭建人员。以下用一页纸说明本技能能做什么、不能做什么。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入处理 | 接受用户提供的 URL、文件路径、粘贴文本、批量清单 | 不接受二进制大文件（>10MB）或加密内容 |
| 资产类型 | 识别 Agent、MCP Server、Skill、Prompt 模板、工作流配置 | 不评估资产代码质量，不执行安全审计 |
| 输出形式 | 生成结构化清单（Markdown 表格 / JSON）、分类汇总、字段提取 | 不生成可直接部署的完整项目代码 |
| 信息处理 | 保留关键元数据（名称、版本、用途、依赖、来源） | 不推断未明确给出的信息，不补全缺失字段 |
| 批量操作 | 支持一次处理多条记录，统一格式输出 | 不支持跨批次状态记忆，每次调用相互独立 |

**适用对象**：需要从分散来源（GitHub 仓库、博客文章、配置文件）中快速提取资产清单的工程师；需要将非结构化文本转为统一格式的自动化脚本编写者；需要对比多个同类工具特征的选型人员。

**不适用对象**：需要深度代码审查的场景；需要实时联网抓取动态页面的场景（本技能仅处理用户已提供的内容）。

---

## 二、触发方式与场景映射

当对话中出现以下意图时，本技能将被激活。下表将触发词与真实使用场景对应，便于快速判断。

| 触发词/短语 | 典型用户表述 | 对应处理模式 |
|-------------|--------------|--------------|
| awesome-claude | “帮我整理这个 awesome-claude 仓库里的资产” | 仓库清单提取 |
| claude资产 | “把这份 Claude 资产列表按类型分个类” | 分类汇总 |
| ai工作流 | “这几个工作流配置帮我对比一下差异” | 字段对比 |
| mcp服务器 | “从这段文本里找出所有 MCP 服务器条目” | 实体抽取 |
| 技能检索 | “在下面这批技能描述里筛出能做文档处理的” | 条件筛选 |
| 工作流导航 | “把这份导航文档转成表格给我” | 格式转换 |

**触发判定规则**：用户消息中命中任一触发词，且包含可处理的具体内容（URL、文件路径、粘贴文本），即进入标准流程。若仅有触发词而无具体输入，技能将输出输入格式示例并等待用户补充。

---

## 三、标准处理流程

### 3.1 前置条件

开始处理前，请确认以下条件是否满足：

| 条件项 | 要求 | 不满足时的处理 |
|--------|------|----------------|
| 输入内容 | 文本格式，可识别编码（UTF-8/GBK） | 提示用户转换为纯文本后重试 |
| 输入规模 | 单次不超过 500 条记录或 50,000 字符 | 建议分批提交，每批 ≤ 上述阈值 |
| 输出格式 | 用户指定或默认 Markdown 表格 | 用户可随时切换为 JSON 格式 |
| 信息完整度 | 至少包含名称字段 | 缺少关键字段时按 3.4 节处理 |

### 3.2 执行步骤

**第一步：解析输入内容**

- 若输入为 URL：提取页面正文文本，去除导航、页脚、广告等噪声内容。
- 若输入为文件路径：读取文件内容，识别文件类型（.md / .json / .txt / .csv）。
- 若输入为粘贴文本：直接作为原始内容进入解析环节。

**第二步：识别关键信息**

按以下优先级提取字段（存在则提取，不存在则跳过）：

| 优先级 | 字段名 | 提取规则 |
|--------|--------|----------|
| P0 | name | 资产名称，通常为标题或首个加粗字段 |
| P0 | type | 资产类型（agent / mcp-server / skill / prompt / workflow） |
| P1 | description | 用途描述，取首段完整句子 |
| P1 | source | 来源标识（GitHub 路径 / 作者名 / 域名） |
| P2 | version | 版本号，匹配语义化版本模式（如 v1.2.3） |
| P2 | dependencies | 依赖项，从配置块或依赖清单中提取 |

**第三步：按规则处理**

- 分类规则：type 字段缺失时，根据 description 关键词推断（含“server”且上下文为连接器 → mcp-server；含“prompt”或“模板” → prompt；含“自动”或“流程” → workflow；其余归为 agent）。
- 去重规则：name 与 source 均相同视为重复记录，仅保留首条。
- 排序规则：默认按 type 分组，组内按 name 字母序排列。

**第四步：生成结果并标注置信度**

每条记录附加 `confidence` 字段，取值规则如下：

| 置信度 | 判定条件 |
|--------|----------|
| high | 所有 P0 字段均直接提取成功，无推断 |
| medium | P0 字段中至少一项为推断得出 |
| low | 存在 P0 字段缺失，或输入内容噪声过大 |

### 3.3 输出规范

**默认输出（Markdown 表格）**：

```markdown
| 名称 | 类型 | 描述 | 来源 | 版本 | 置信度 |
|------|------|------|------|------|--------|
| example-agent | agent | 示例代理，用于演示 | github.com/example | v1.0.0 | high |
```

**可选输出（JSON 数组）**：

```json
[
  {
    "name": "example-agent",
    "type": "agent",
    "description": "示例代理，用于演示",
    "source": "github.com/example",
    "version": "v1.0.0",
    "confidence": "high"
  }
]
```

**自查清单**（输出前逐项确认）：

- [ ] 所有 P0 字段是否已填充（缺失项是否已标注 `[需核实:字段名]`）
- [ ] 格式是否为用户指定格式（默认 Markdown 表格）
- [ ] 每条记录是否附带置信度标注
- [ ] 重复记录是否已去重

### 3.4 置信度门控

当输入信息不足以支撑可靠输出时，遵循以下原则：

1. **不编造**：任何无法从输入中直接获取的字段，一律输出 `[需核实:字段名]` 占位符，不得猜测填充。
2. **主动提示**：若某条记录缺失 P0 字段（name 或 type），在输出末尾追加提示：“第 N 条记录缺少 [字段名]，请补充后重试以获得完整结果。”
3. **二次确认**：当推断字段占比超过 30% 时，输出结果前先询问用户：“检测到较多推断字段，是否继续输出？或补充原始材料后重新处理？”

---

## 四、错误码体系

| 错误码 | 错误场景 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 输入为空或全为空白字符 | “未检测到有效输入内容，请提供 URL、文件路径或粘贴文本。” | 引导用户提供具体内容后重试 |
| E002 | 输入格式无法解析（如乱码、非文本） | “输入内容无法解析为文本，请确认文件为纯文本格式（.txt/.md/.json/.csv）。” | 建议用户转换格式后重新提交 |
| E003 | 未识别到任何资产记录 | “在输入内容中未找到符合资产特征（名称+类型）的记录。” | 提供正确输入格式示例（见 4.1 节） |
| E004 | 单次处理超过规模上限 | “输入规模超过单次处理上限（500 条 / 50,000 字符），请分批提交。” | 指导用户拆分输入后分批处理 |
| E005 | 输出格式参数无效 | “输出格式仅支持 markdown 或 json，请重新指定。” | 列出合法参数值并等待用户重新输入 |

### 4.1 正确输入格式示例

```
# 资产清单

## agent
- name: doc-helper
  description: 文档处理辅助代理
  source: github.com/example/doc-helper
  version: v2.1.0

## mcp-server
- name: file-bridge
  description: 文件系统桥接服务器
  source: github.com/example/file-bridge
```

---

## 五、FAQ 与反模式对照

| 常见坑 | 反模式（错误做法） | 正模式（推荐做法） |
|--------|--------------------|--------------------|
| 输入信息不足时强行输出 | 对缺失字段随意填写“未知”或猜测值 | 使用 `[需核实:字段名]` 占位，并提示用户补充 |
| 混淆资产类型 | 将所有条目统一归类为 agent | 依据 description 关键词与上下文推断，并标注置信度 |
| 忽略重复记录 | 原样输出所有条目，不做去重 | 按 name+source 去重，保留首条 |
| 输出格式不一致 | 部分条目用表格、部分用列表 | 统一为单一格式（默认 Markdown 表格） |
| 批量处理时丢失上下文 | 将批次间状态混淆，导致重复或遗漏 | 每次调用独立处理，批次间不做状态关联 |

---

## 六、渐进式披露阅读路径

### 6.1 速查卡（30 秒上手）

1. 提供输入（URL / 文件 / 粘贴文本）
2. 指定输出格式（默认 Markdown 表格）
3. 获取结构化清单（含置信度标注）
4. 缺失字段以 `[需核实:xxx]` 占位

### 6.2 新手路径（首次使用）

- 阅读「一、能力边界速查卡」了解适用范围
- 阅读「三、标准处理流程」的 3.1 与 3.2 节，掌握输入要求与基本步骤
- 遇到问题对照「四、错误码体系」定位并修正

### 6.3 进阶路径（深度使用）

- 深入理解「3.2 执行步骤」中的字段提取优先级与推断规则
- 掌握「3.4 置信度门控」的判定逻辑，合理利用二次确认机制
- 结合「五、FAQ 与反模式对照」优化输入质量，提升输出准确率

---

## 七、参数速查表

| 参数名 | 类型 | 默认值 | 合法值 | 说明 |
|--------|------|--------|--------|------|
| output_format | string | markdown | markdown / json | 输出结构格式 |
| deduplicate | boolean | true | true / false | 是否按 name+source 去重 |
| sort_by | string | type | type / name / none | 结果排序字段 |
| max_records | integer | 500 | 1-500 | 单次处理最大记录数 |
| include_confidence | boolean | true | true / false | 是否输出置信度列 |

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者应自行承担因使用本 Skill 及其输出结果所产生的一切责任与风险。本 Skill 提供的处理结果仅供参考，不构成任何形式的保证或承诺。
2. **禁止反向工程**：使用者不得对本 Skill 的底层逻辑、提示词结构、评分机制进行反向工程、破解、提取或二次分发。
3. **合规使用**：使用者应确保输入内容不违反法律法规及平台政策，因输入内容引发的侵权、违规等问题由使用者自行承担。
4. **服务变更**：本 Skill 可能随时更新或终止服务，恕不另行通知。

<!-- user-agreement-injected -->

---

## 许可证（License）

本 Skill 采用 MIT 许可证发布。

```
MIT License

Copyright (c) 2026 LingFlow Studio

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

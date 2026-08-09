---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: awesome-chatgpt-repositories
name: awesome-chatgpt-repositories
displayName: ChatGPT开源仓库检索 项目筛选 资源导航
description: 检索并整理ChatGPT相关开源仓库，输出结构化清单。
version: 1.0.1
rules_version: cpr-20260809-n251
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/awesome-chatgpt-repositories
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Ling
agent_created: true
trigger_words: ["awesome-chatgpt-repositories", "ChatGPT仓库", "开源项目检索", "OpenAI仓库", "Codex项目", "仓库清单"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# ChatGPT 开源仓库检索与整理

## 一、能力边界速查卡

| 维度 | 说明 |
|------|------|
| ✅ 能做 | 解析用户提供的仓库列表、URL、文本数据，提取仓库名称、描述、星标数、语言、许可证等字段 |
| ✅ 能做 | 按主题（ChatGPT / OpenAI API / Codex）或自定义条件（语言、星标阈值）过滤仓库 |
| ✅ 能做 | 输出 Markdown 表格、CSV、JSON 三种格式的结构化清单 |
| ✅ 能做 | 对缺失字段标注 `[需核实:字段名]`，不猜测补全 |
| ✅ 能做 | 批量处理多条仓库记录，支持去重与排序 |
| ❌ 不能做 | 实时抓取 GitHub 数据（需用户提供数据源或 URL 内容） |
| ❌ 不能做 | 评估仓库代码质量或安全性（仅整理元数据） |
| ❌ 不能做 | 自动推荐"最佳"仓库（可排序，不下结论） |
| ❌ 不能做 | 处理非仓库类内容（如教程文章、付费产品链接） |

**适用对象**：需要快速浏览大量 ChatGPT 相关开源项目、做技术选型预筛选、或整理资源清单的开发者、技术博主、研究爱好者。

---

## 二、触发方式与场景映射

| 用户说（大白话） | 触发动作 |
|------------------|----------|
| "帮我整理这份 ChatGPT 仓库列表" | 解析输入，输出结构化清单 |
| "筛选出 Python 写的 OpenAI 项目" | 按语言过滤 |
| "把星标超过 5000 的排前面" | 按星标数降序排序 |
| "转成 CSV 给我" | 输出 CSV 格式 |
| "这个仓库是干嘛的？" | 提取该仓库描述并解释 |

**触发词**：`awesome-chatgpt-repositories`、`ChatGPT仓库`、`开源项目检索`、`OpenAI仓库`、`Codex项目`、`仓库清单`、`GitHub项目整理`、`仓库筛选`。

---

## 三、标准处理流程

### 前置条件

- 用户需提供至少一条仓库记录（名称或 URL），或一份包含多条记录的文本/文件。
- 若输入为空，返回错误码 `E001` 并附正确输入示例。

### 执行步骤

1. **收集输入**：接收用户粘贴的文本、上传的文件（.txt / .csv / .json / .md）或 URL 内容。
2. **解析记录**：按行或按分隔符拆分，识别每条仓库记录。支持格式：
   - `owner/repo`（如 `openai/chatgpt`）
   - 完整 URL（如 `https://github.com/openai/chatgpt`）
   - 带描述的行（如 `openai/chatgpt - ChatGPT desktop app`）
3. **字段提取**：从每条记录中提取以下字段（缺失则标注 `[需核实:字段名]`）：
   - `name`：仓库全名（owner/repo）
   - `url`：GitHub 地址
   - `description`：仓库描述（若输入中未提供，标注需核实）
   - `language`：主要编程语言（若输入中未提供，标注需核实）
   - `stars`：星标数（若输入中未提供，标注需核实）
   - `license`：许可证类型（若输入中未提供，标注需核实）
4. **过滤与排序**（可选）：
   - 按语言过滤：`language:Python`
   - 按星标阈值过滤：`stars:>5000`
   - 按主题过滤：`topic:chatgpt` / `topic:openai-api` / `topic:codex`
   - 排序规则：`sort:stars-desc`（默认）或 `sort:name-asc`
5. **去重**：若多条记录指向同一仓库，保留信息最完整的一条。
6. **生成输出**：按约定格式输出（见下节）。
7. **自查**：检查字段完整性、格式正确性、置信度标注是否齐全。

### 输出规范

| 输出格式 | 适用场景 | 示例 |
|----------|----------|------|
| Markdown 表格 | 默认格式，适合阅读 | 见下方示例 |
| CSV | 需要导入表格工具 | `name,url,description,language,stars,license` |
| JSON | 需要程序化处理 | `[{"name":"openai/chatgpt","url":"...","stars":12345}]` |

**Markdown 表格示例**：

| 仓库名 | 描述 | 语言 | 星标 | 许可证 |
|--------|------|------|------|--------|
| openai/chatgpt | ChatGPT desktop application | TypeScript | 45000 | [需核实:license] |
| acheong08/ChatGPT | Reverse engineered ChatGPT API | Python | 28000 | MIT |

---

## 四、置信度门控

- 当输入中缺少某字段且无法推断时，输出 `[需核实:字段名]`，**绝不编造**。
- 当输入来源为二手整理（非官方 GitHub 页面）时，在输出末尾附加说明：`数据来源为二手整理，星标数与描述可能滞后，建议以 GitHub 页面为准。`
- 当用户要求排序但未指定排序字段时，默认按星标数降序，并在输出中注明排序规则。

---

## 五、错误码体系

| 错误码 | 触发条件 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `E001` | 输入为空或无法识别 | "未检测到有效的仓库记录。请提供 GitHub 仓库名（如 `openai/chatgpt`）或完整 URL。" | 引导用户粘贴仓库列表或文件 |
| `E002` | 输入包含非仓库内容 | "检测到部分内容不是有效的 GitHub 仓库，已跳过。请确认输入格式。" | 展示跳过的条目，让用户确认是否保留 |
| `E003` | 过滤条件无匹配结果 | "没有找到符合过滤条件的仓库。请放宽条件或检查拼写。" | 建议降低星标阈值或移除语言过滤 |
| `E004` | 输出格式不支持 | "暂不支持该输出格式。当前支持：Markdown 表格、CSV、JSON。" | 列出支持格式，请用户重新选择 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|--------------------|----------|
| 编造星标数 | 输入没写星标，直接填 10000 | 标注 `[需核实:stars]` |
| 混淆同名仓库 | 只按仓库名去重，忽略 owner | 按 `owner/repo` 全名去重 |
| 忽略许可证缺失 | 默认填 MIT | 标注 `[需核实:license]` |
| 排序规则不透明 | 排序后不说明依据 | 在输出末尾注明排序字段与方向 |
| 过度解读描述 | 把描述翻译成"最强大的项目" | 保留原文描述，不做价值判断 |

---

## 七、渐进式阅读路径

### 新手路径（5 分钟上手）

1. 阅读「能力边界速查卡」了解能做什么。
2. 直接粘贴仓库列表，使用默认格式输出。
3. 如需过滤，参考「执行步骤」第 4 条的过滤语法。

### 进阶路径（深度使用）

1. 掌握全部字段提取规则与置信度门控逻辑。
2. 自定义输出格式（CSV / JSON）对接自己的工具链。
3. 结合错误码体系排查输入格式问题。
4. 批量处理多份数据源，合并去重后生成统一清单。

---

## 八、用户协议

使用本 Skill 即表示您同意以下条款：

- **责任承担**：使用者自行承担全部责任。本 Skill 输出的内容基于用户提供的输入，不构成任何形式的保证或建议。
- **禁止反向工程**：不得对本 Skill 的提示词、内部逻辑进行反向工程、提取或再分发。
- **合规使用**：使用者需确保输入数据来源合法，不得用于侵犯他人知识产权或违反 GitHub 服务条款的行为。
- **免责声明**：本 Skill 由 AI 辅助生成，仅供学习参考，不提供任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

本 Skill 采用 MIT 许可证发布。

```
MIT License

Copyright (c) 2025 Ling

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

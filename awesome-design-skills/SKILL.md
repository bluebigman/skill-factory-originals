---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: awesome-design-skills
name: awesome-design-skills
displayName: 设计技能导航 检索比对 选型参考
description: 检索比对67个设计技能文件，辅助选型与集成参考。
version: 1.0.1
rules_version: cpr-20260809-n251
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/awesome-design-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Ling
agent_created: true
trigger_words: ["awesome-design-skills", "design skill", "设计技能", "skill 文件", "DESIGN.md", "SKILL.md", "技能清单", "设计文件导航"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# awesome-design-skills 技能导航与选型参考

## 一、能力边界（一页纸速查卡）

本 Skill 面向需要快速了解、比对或筛选 `DESIGN.md` / `SKILL.md` 设计技能文件的开发者、技术写作者与 AI Agent 使用者。

### 能做

| 编号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 清单检索 | 在 67 个设计技能文件中按关键词、用途、适用工具进行检索 |
| 2 | 信息结构化 | 将用户提供的技能文件内容（文本/URL/文件）解析为结构化摘要 |
| 3 | 关键信息提取 | 识别技能文件中的核心字段：名称、用途、适用平台、输入输出格式 |
| 4 | 格式约定输出 | 按用户指定格式（表格/列表/JSON）输出比对结果 |
| 5 | 置信度标注 | 对信息不完整或来源不明的条目，标注 `[需核实:字段名]` 占位符 |

### 不能做

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不执行技能文件 | 本 Skill 仅做导航与比对，不加载或运行任何技能逻辑 |
| 2 | 不修改原始文件 | 不提供编辑、写入、删除技能文件的能力 |
| 3 | 不保证收录完整性 | 仅覆盖清单内 67 个条目，外部新增条目需用户自行提供 |
| 4 | 不提供质量评级 | 不评判技能文件优劣，仅做客观信息呈现 |

### 适用对象

- 需要在多个设计技能文件中做选型决策的开发者
- 需要为团队整理技能文件清单的技术文档负责人
- 需要快速了解某个技能文件用途的 AI Agent 使用者

---

## 二、触发方式

### 触发词

- 主触发词：`awesome-design-skills`
- 同义触发词：`设计技能导航`、`技能文件清单`、`DESIGN.md 列表`、`SKILL.md 检索`

### 场景映射表

| 用户说（大白话） | 触发动作 |
|------------------|----------|
| "帮我看看有哪些设计技能文件" | 输出 67 个条目的分类概览 |
| "这个技能文件是干什么的" | 解析用户提供的文件内容，输出结构化摘要 |
| "对比一下这两个 skill 的输入输出" | 提取两个文件的输入输出字段做并排比对 |
| "有哪些适合 Claude Design 的技能" | 按适用平台过滤清单 |
| "这个文件里没写版本号" | 标注 `[需核实:version]` 并提示用户补充 |

---

## 三、标准流程

### 前置条件

| 条件 | 要求 |
|------|------|
| 输入来源 | 用户提供的数据、文件路径、URL，或直接引用清单内条目名称 |
| 输入格式 | 文本、Markdown 文件、JSON、URL 链接均可 |
| 环境要求 | 无特殊依赖，纯文本处理 |

### 执行步骤

1. **接收输入**：确认用户提供的是文件内容、URL 还是清单内条目名称。
2. **解析内容**：识别技能文件中的关键字段（名称、描述、适用平台、输入输出格式、版本号）。
3. **结构化处理**：按以下规则整理信息：
   - 字段缺失 → 标注 `[需核实:字段名]`
   - 字段冲突 → 保留全部值，标注 `[冲突:字段名]`
   - 信息模糊 → 标注 `[需核实:描述]`
4. **生成结果**：按用户指定格式（默认表格）输出。
5. **自查校验**：检查字段完整性、格式正确性、置信度标注是否到位。
6. **二次确认**：若关键字段缺失影响判断，向用户提问补充。

### 输出规范

| 输出项 | 格式要求 |
|--------|----------|
| 默认格式 | Markdown 表格（名称 / 用途 / 适用平台 / 输入 / 输出 / 置信度） |
| 批量比对 | 并排表格，每列一个技能文件 |
| JSON 输出 | 数组结构，每个对象含 `name`、`description`、`platform`、`input`、`output`、`confidence` 字段 |

---

## 四、置信度门控

### 规则说明

| 场景 | 处理方式 |
|------|----------|
| 字段缺失 | 输出 `[需核实:字段名]`，不猜测填充 |
| 来源不明确 | 标注 `[需核实:来源]`，提示用户提供原始链接 |
| 信息自相矛盾 | 保留全部值，标注 `[冲突:字段名]` |
| 超出清单范围 | 提示"该条目不在收录清单内"，请用户提供文件内容 |

### 示例

用户提供一段技能文件描述，缺少版本号：

```text
输入：一个名为 "data-mapper" 的技能文件，描述为"将 CSV 转换为 JSON"，无版本号。
输出：
| 名称 | 用途 | 版本 | 置信度 |
|------|------|------|--------|
| data-mapper | 将 CSV 转换为 JSON | [需核实:version] | 中 |
```

---

## 五、错误码体系

| 错误码 | 场景 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 输入为空 | "未检测到输入内容，请提供文件路径、URL 或技能名称。" | 引导用户补充输入 |
| E002 | 输入格式无法解析 | "无法解析该输入，请确认为文本、Markdown 或 JSON 格式。" | 展示正确格式示例 |
| E003 | 条目不在清单内 | "该名称不在 67 个收录条目中，请提供文件内容以便解析。" | 请用户粘贴内容或提供 URL |
| E004 | 关键字段全部缺失 | "未提取到任何有效字段，请检查文件是否为有效的技能文件格式。" | 展示标准技能文件结构示例 |
| E005 | 批量比对数量超限 | "单次比对最多支持 5 个文件，请分批操作。" | 提示分批处理 |

---

## 六、FAQ 反模式

| 常见坑 | 反模式对照 |
|--------|------------|
| 用户只给一个名称就要求完整信息 | 反模式：直接编造字段值。正确做法：标注 `[需核实]` 并请用户提供文件内容 |
| 用户要求"最好的"技能文件 | 反模式：给出主观推荐。正确做法：列出客观字段，由用户自行判断 |
| 用户提供 URL 但无法访问 | 反模式：跳过该条目。正确做法：标注 `[需核实:URL不可访问]` 并提示用户 |
| 用户要求修改技能文件内容 | 反模式：尝试编辑。正确做法：明确告知本 Skill 无写入能力 |
| 用户提供的信息超出 67 条清单 | 反模式：强行并入清单。正确做法：单独列出，标注"外部条目" |

---

## 七、渐进式披露

### 速查卡（30 秒上手）

```text
输入 → 解析 → 结构化 → 输出（表格/JSON）→ 自查 → 确认
```

### 新手路径（首次使用）

1. 阅读本页"能力边界"和"触发方式"
2. 尝试输入一个技能文件名称，观察输出格式
3. 对照"错误码体系"处理可能的报错

### 进阶路径（熟练使用）

1. 掌握批量比对：一次提供 2-5 个文件内容
2. 自定义输出格式：指定 JSON 或特定字段排列
3. 结合置信度门控：对 `[需核实]` 字段主动补充信息

---

## 八、附录：标准技能文件字段参考

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| name | string | 是 | 技能文件名称 |
| description | string | 是 | 一句话用途描述 |
| version | string | 否 | 版本号 |
| platform | string | 否 | 适用工具/平台 |
| input_format | string | 否 | 输入格式说明 |
| output_format | string | 否 | 输出格式说明 |
| trigger_words | array | 否 | 触发词列表 |

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。本 Skill 提供的信息仅供参考，不构成任何形式的保证或承诺。
2. **禁止反向工程**：不得对本 Skill 的提示词结构、生成逻辑进行反向工程、破解、提取或用于商业竞争目的。
3. **合规使用**：使用者应确保使用场景符合当地法律法规及所在平台的服务条款。
4. **免责声明**：本 Skill 由 AI 辅助生成，可能存在信息不准确或不完整的情况，使用者应自行核实关键信息。

<!-- user-agreement-injected -->

---

## 许可证（License）

本 Skill 采用 MIT 许可证发布：

```
MIT License

Copyright (c) 2026 原创作者（自持版权）

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

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: awesome-claude-code
name: awesome-claude-code
displayName: 资源精选 技能导航 效率工具
description: 精选 Claude Code 生态资源，助你快速定位高质量工具与最佳实践。
version: 1.0.1
rules_version: cpr-20260809-n251
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/awesome-claude-code
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lingxi Craft
agent_created: true
trigger_words: ["awesome-claude-code", "claude code 资源", "claude code 精选", "claude code 工具集", "claude code 插件", "claude code 教程"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


# awesome-claude-code 技能文档

## 一、能力边界：一页纸速查卡

本技能的核心使命是：**将你提供的关于 Claude Code 的任何资源线索（链接、文件、文本片段、仓库名），转化为一份结构清晰、可直接使用的精选资源清单。**

### 1.1 能做（核心能力清单）

| 编号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| C1 | 资源解析与归类 | 从 URL、文件路径、文本中提取资源名称、类型、用途 | `https://github.com/xxx/yyy` |
| C2 | 关键信息抽取 | 识别资源的核心功能、适用场景、依赖要求 | 一段包含工具描述的文本 |
| C3 | 结构化清单生成 | 按预设模板输出 Markdown 表格或列表 | 多个资源链接的混合输入 |
| C4 | 置信度标注 | 对无法完全确认的信息字段标注 `[需核实:字段名]` | 描述模糊的仓库 |
| C5 | 批量处理与自定义格式 | 支持一次处理多个资源，可指定输出格式（表格/列表/JSON） | 包含 10 个链接的文档 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不生成新资源 | 不会凭空创造不存在的工具或项目 |
| L2 | 不验证资源可用性 | 不负责检查链接是否失效、代码是否可运行 |
| L3 | 不提供深度评测 | 不输出主观使用体验或性能对比结论 |
| L4 | 不处理非 Claude Code 相关资源 | 与 Claude Code 生态无关的内容将忽略并提示 |

### 1.3 适用对象

- **新手用户**：刚接触 Claude Code，需要一份入门资源清单。
- **进阶开发者**：寻找特定类型的插件、工作流或集成方案。
- **技术调研者**：需要快速梳理某个主题下的资源全景。

---

## 二、触发方式：场景映射表

当你的输入包含以下关键词或意图时，本技能将被激活：

| 触发词/场景 | 用户可能说的话（大白话） | 技能响应 |
|-------------|--------------------------|----------|
| `awesome-claude-code` | “帮我看看 awesome-claude-code 里有什么” | 解析并输出精选资源清单 |
| `claude code 资源` | “有没有好用的 Claude Code 插件推荐？” | 收集输入并生成结构化推荐 |
| `claude code 精选` | “整理一下我收藏的这些 Claude Code 工具” | 对提供的链接/文件进行归类整理 |
| `claude code 工具集` | “把这份文档里的工具都列出来” | 从文本中抽取工具信息并格式化 |
| `claude code 教程` | “我想找 Claude Code 的学习资料” | 筛选教程类资源并单独列出 |
| 其他同义表达 | “帮我整理一下这些链接”、“这个仓库是干嘛的” | 按标准流程处理 |

---

## 三、标准流程：从输入到输出

### 3.1 前置条件

- **输入要求**：至少包含一个可识别的资源线索（URL、文件路径、仓库名、工具名称）。
- **格式建议**：多个资源请用换行、逗号或分号分隔。
- **可选参数**：可通过自然语言指定输出格式（如“用表格”、“只要名称和简介”）。

### 3.2 执行步骤（分步编号）

**Step 1：收集与确认**
- 接收用户输入，识别其中的资源线索。
- 若输入为空或无法识别，返回错误码 `E100`。

**Step 2：解析与分类**
- 对每个资源线索执行以下操作：
  1. 提取资源名称（仓库名/工具名/标题）。
  2. 判断资源类型（插件/教程/工作流/集成/其他）。
  3. 从描述文本中抽取核心功能关键词。
- 分类规则参考下表：

| 类型标识 | 关键词示例 | 归类结果 |
|----------|------------|----------|
| `plugin`, `extension`, `addon` | 插件、扩展 | `plugin` |
| `tutorial`, `guide`, `docs`, `course` | 教程、指南、文档 | `tutorial` |
| `workflow`, `automation`, `pipeline` | 工作流、自动化 | `workflow` |
| `integration`, `api`, `sdk` | 集成、接口 | `integration` |
| 其他 | 无法匹配 | `other` |

**Step 3：生成结果并标注置信度**
- 对每个字段进行置信度评估：
  - **高置信度**（≥90%）：信息直接从输入中明确提取。
  - **中置信度**（70%-89%）：信息通过上下文推断。
  - **低置信度**（<70%）：信息模糊，标注 `[需核实:字段名]`。
- 置信度标注规则：
  - 仅在低置信度时显式标注。
  - 标注格式：`[需核实:资源名称]`、`[需核实:功能描述]`。

**Step 4：输出与自查**
- 按约定格式输出结果（见 3.3）。
- 自查清单：
  - [ ] 所有输入资源均已处理
  - [ ] 每个资源至少包含名称和类型
  - [ ] 低置信度字段已标注
  - [ ] 输出格式符合要求

### 3.3 输出规范

**默认输出格式（Markdown 表格）：**

```markdown
| 资源名称 | 类型 | 核心功能 | 来源 | 置信度 |
|----------|------|----------|------|--------|
| example-tool | plugin | 自动补全 | https://... | 高 |
| guide-book | tutorial | 入门教程 | 本地文件 | [需核实:功能描述] |
```

**自定义格式支持：**
- `列表模式`：使用无序列表逐条输出。
- `JSON 模式`：输出结构化 JSON 数组。
- `详细模式`：每个资源附带一段描述文字。

---

## 四、置信度门控：不编造原则

当遇到以下情况时，必须使用 `[需核实:字段]` 占位，**严禁**自行推断或编造：

| 场景 | 处理方式 | 示例 |
|------|----------|------|
| 输入只有链接，无任何描述 | 名称从链接提取，功能描述标注 `[需核实:功能描述]` | `[需核实:功能描述]` |
| 描述存在歧义 | 选择最可能的解释，并标注 `[需核实:类型]` | `[需核实:类型]` |
| 资源名称疑似拼写错误 | 保留原样，标注 `[需核实:资源名称]` | `[需核实:资源名称]` |
| 无法判断资源相关性 | 标注 `[需核实:是否与Claude Code相关]` | `[需核实:是否与Claude Code相关]` |

**门控规则**：
1. 任何字段的置信度低于 70%，必须标注。
2. 标注后，在输出末尾附注：“标注 [需核实] 的字段请用户确认后使用。”
3. 若超过 50% 的字段需要核实，建议用户补充信息后重新处理。

---

## 五、错误码体系

| 错误码 | 错误描述 | 用户提示话术 | 修正步骤 |
|--------|----------|--------------|----------|
| `E100` | 输入为空或无法识别 | “未检测到有效的资源线索。请提供至少一个 URL、文件路径或工具名称。” | 1. 检查输入是否包含链接或文件名<br>2. 重新发送包含资源线索的消息 |
| `E101` | 输入内容与 Claude Code 无关 | “检测到输入内容与 Claude Code 生态无关，已忽略。请提供相关资源。” | 1. 确认资源是否与 Claude Code 相关<br>2. 移除无关内容后重试 |
| `E102` | 输出格式指定无效 | “不支持的输出格式。可选格式：表格、列表、JSON、详细。” | 1. 使用支持的格式关键词<br>2. 重新指定格式 |
| `E103` | 批量处理超限 | “单次处理的资源数量超过上限（50 个）。请分批提交。” | 1. 将资源分为多批<br>2. 逐批提交处理 |
| `E104` | 文件读取失败 | “无法读取提供的文件。请检查文件路径或权限。” | 1. 确认文件存在且可读<br>2. 将文件内容粘贴为文本后重试 |

---

## 六、FAQ 反模式：常见坑与对照

### 6.1 常见坑

| 坑编号 | 常见错误操作 | 后果 | 正确做法 |
|--------|--------------|------|----------|
| P1 | 只发一个链接，不附带任何说明 | 输出中大量字段被标注 `[需核实]` | 提供链接时附上一句话描述 |
| P2 | 一次性提交 100+ 个资源 | 触发 `E103` 错误 | 分批提交，每批不超过 50 个 |
| P3 | 要求“推荐最好的工具” | 违反绝对化用语禁令，无法响应 | 改为“按功能分类列出工具” |
| P4 | 输入包含多个不相关主题 | 部分资源被忽略或误分类 | 按主题分开提交 |
| P5 | 要求验证链接是否有效 | 超出能力边界（L2） | 自行访问链接验证 |

### 6.2 反模式对照表

| 反模式 | 反例（错误） | 正例（正确） |
|--------|--------------|--------------|
| 绝对化承诺 | “这个工具是最好用的” | “这个工具在自动补全方面表现突出” |
| 编造信息 | “该工具支持 X 功能”（实际未提及） | “该工具支持 X 功能 [需核实:功能描述]” |
| 忽略边界 | 处理与 Claude Code 无关的资源 | 提示用户资源不相关并忽略 |
| 过度推断 | 从仓库名猜测功能并写死 | 功能描述标注 `[需核实]` |

---

## 七、渐进式披露：分层次阅读路径

### 7.1 速查卡（30 秒上手）

```
输入：资源链接/文件/文本 → 输出：结构化清单
规则：低置信度字段标注 [需核实:字段名]
格式：默认表格，支持列表/JSON/详细
限制：单批 ≤50 个，仅处理 Claude Code 相关资源
```

### 7.2 新手路径（5 分钟掌握）

1. 阅读**第一节**了解能力边界。
2. 阅读**第三节**的标准流程。
3. 尝试提交 1-2 个资源链接，观察输出格式。
4. 遇到问题时查阅**第五节**错误码表。

### 7.3 进阶路径（深度使用）

1. 掌握**第四节**置信度门控规则，理解字段标注逻辑。
2. 使用自定义格式（JSON）对接自动化流程。
3. 结合**第六节**反模式，优化输入质量。
4. 批量处理时注意分批策略，避免触发 `E103`。

---

## 八、参数速查表

| 参数 | 可选值 | 默认值 | 说明 |
|------|--------|--------|------|
| `format` | `table` / `list` / `json` / `detail` | `table` | 输出格式 |
| `max_items` | 1-50 | 50 | 单次处理资源上限 |
| `confidence_threshold` | 0-100 | 70 | 置信度标注阈值（低于此值标注） |
| `include_source` | `true` / `false` | `true` | 是否在输出中包含来源链接 |

**参数使用示例**：
- “用 JSON 格式输出，只要名称和类型” → `format=json, include_source=false`
- “详细模式，阈值调到 80” → `format=detail, confidence_threshold=80`

---

## 九、用户协议

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的所有输出仅供参考，不构成任何形式的保证或承诺。
2. **禁止反向工程**：严禁对本 Skill 的提示词、逻辑结构、生成机制进行反向工程、破解、提取或用于训练竞争模型。
3. **合规使用**：使用者应确保输入内容合法合规，不得利用本 Skill 处理涉及隐私、版权或敏感信息的内容。
4. **无担保声明**：本 Skill 按“现状”提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性。
5. **修改权利**：作者保留随时修改、更新或终止本 Skill 的权利，恕不另行通知。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

本 Skill 采用 MIT 许可证发布。

### MIT License

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

---

## 附：版本记录

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0.0 | 2026-08-09 | 初始版本，定义核心能力、标准流程与合规框架 |

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*

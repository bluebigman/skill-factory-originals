---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: awesome-hermes-skills
name: awesome-hermes-skills
displayName: 技能装配 场景匹配 能力速查
description: 面向 Hermes Agent 的技能目录导航与装配决策参考。
version: 1.0.1
rules_version: cpr-20260809-n251
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/awesome-hermes-skills
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["awesome-hermes-skills", "hermes技能", "技能列表", "skill目录", "技能导航", "技能装配", "能力速查"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# awesome-hermes-skills 技能导航与装配指南

## 一、能力边界：一页纸速查卡

本 Skill 面向 Hermes Agent（v0.17.0）用户，提供技能目录的导航、筛选与装配决策支持。它不是一个执行引擎，而是一张地图——告诉你有什么可用、怎么选、怎么装。

### 1.1 能做（核心能力清单）

| 编号 | 能力项 | 说明 | 适用场景示例 |
|------|--------|------|--------------|
| C1 | 技能目录索引 | 提供 72 个内置 + 101 个可选捆绑 + 85 个社区技能的结构化索引 | 快速了解平台技能全貌 |
| C2 | 装配决策支持 | 根据用户任务描述，推荐匹配的技能组合 | 接到新任务时选择合适工具 |
| C3 | 输入解析与结构化 | 将用户提供的数据/文件/URL 解析为结构化结果 | 从 URL 提取技能元数据 |
| C4 | 关键信息识别 | 从输入中提取技能名称、版本、依赖、触发词等关键字段 | 批量整理技能清单 |
| C5 | 批量处理与自定义格式 | 支持多技能条目批量处理，按用户指定格式输出 | 生成自定义格式的技能报表 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不执行技能安装 | 本 Skill 仅提供导航与建议，不直接操作文件系统或执行安装命令 |
| L2 | 不保证技能兼容性 | 不承担因版本差异导致的运行异常责任 |
| L3 | 不生成新技能代码 | 不提供技能开发脚手架或代码生成 |
| L4 | 不评估技能质量 | 不对任何技能做"好/坏"定性评价，仅提供客观属性信息 |

### 1.3 适用对象

- **新手用户**：刚接触 Hermes Agent，需要了解有哪些技能可用
- **进阶用户**：有明确任务目标，需要快速匹配合适技能
- **批量管理者**：需要整理、归档、导出技能清单的运维人员

---

## 二、触发方式：场景映射表

当你的输入命中以下任一场景模式时，本 Skill 将被激活：

| 触发词/短语 | 用户意图（大白话） | 本 Skill 的响应行为 |
|-------------|-------------------|---------------------|
| "有哪些技能" | 我想看看平台有什么可用 | 输出技能分类总览 |
| "帮我找个能处理XX的技能" | 我有具体任务，需要工具 | 按任务关键词匹配推荐 |
| "技能列表导出" | 我要把清单存下来 | 按指定格式输出结构化清单 |
| "awesome-hermes-skills" | 直接引用本技能名 | 展示完整导航文档 |
| "技能怎么选" | 我不确定该用哪个 | 提供决策树与筛选建议 |
| "技能目录" / "技能导航" | 我想浏览全貌 | 展示分类索引 |

---

## 三、标准流程：从输入到输出

### 3.1 前置条件

| 条件项 | 要求 | 缺失时的处理 |
|--------|------|--------------|
| 输入内容 | 至少包含一个可识别的任务描述或技能名称关键词 | 返回引导提示，要求补充输入 |
| 输入格式 | 文本、文件路径或 URL 均可 | 自动识别输入类型 |
| 输出格式偏好 | 可选：表格/JSON/Markdown 列表 | 默认输出 Markdown 表格 |

### 3.2 执行步骤

**步骤 1：输入解析**
- 识别输入类型（文本/文件/URL）
- 提取关键词：技能名称、任务描述、分类标签
- 若为 URL，尝试抓取页面内容并解析技能元数据

**步骤 2：匹配与筛选**
- 将解析结果与技能索引库进行匹配
- 匹配维度：名称、描述关键词、分类标签、触发词
- 按相关度排序，取 Top N（默认 5，可配置）

**步骤 3：结果生成**
- 按用户指定格式组织输出
- 每个技能条目包含：名称、版本、分类、一句话描述、触发词
- 标注匹配置信度

**步骤 4：完整性校验**
- 检查必填字段是否齐全
- 检查格式是否符合约定
- 校验置信度标注是否完整

### 3.3 输出规范

**默认输出格式（Markdown 表格）：**

```markdown
| 技能名称 | 版本 | 分类 | 描述 | 触发词 | 置信度 |
|----------|------|------|------|--------|--------|
| skill-name | 1.0.0 | 内置 | 一句话描述 | 触发词1, 触发词2 | 高/中/低 |
```

**JSON 输出格式（当用户指定时）：**

```json
{
  "matches": [
    {
      "name": "skill-name",
      "version": "1.0.0",
      "category": "builtin",
      "description": "一句话描述",
      "trigger_words": ["触发词1", "触发词2"],
      "confidence": 0.85
    }
  ],
  "total": 1,
  "query": "原始查询关键词"
}
```

**置信度标注规则：**

| 置信度等级 | 判定标准 | 适用场景 |
|-----------|----------|----------|
| 高（≥0.85） | 技能名称或描述与查询词完全匹配 | 精确搜索技能名 |
| 中（0.60-0.84） | 描述关键词部分匹配，或分类标签匹配 | 按任务描述搜索 |
| 低（<0.60） | 仅有间接关联，或匹配依据不足 | 模糊搜索、探索性查询 |

---

## 四、置信度门控：不编造原则

当出现以下情况时，本 Skill 将输出占位符而非猜测值：

| 场景 | 处理方式 | 输出示例 |
|------|----------|----------|
| 技能版本信息缺失 | 输出 `[需核实:version]` 占位 | `| skill-x | [需核实:version] | ...` |
| 触发词未收录 | 输出 `[需核实:trigger_words]` 占位 | `| skill-x | 1.0.0 | ... | [需核实:trigger_words] |` |
| 分类归属不明确 | 输出 `[需核实:category]` 占位 | `| skill-x | 1.0.0 | [需核实:category] | ...` |
| 描述信息不足 | 输出 `[需核实:description]` 占位 | `| skill-x | 1.0.0 | ... | [需核实:description] |` |

**铁律**：任何字段在信息不足时，一律使用占位符，严禁根据上下文推测填充。

---

## 五、错误码体系

| 错误码 | 错误描述 | 用户提示话术 | 修正步骤 |
|--------|----------|--------------|----------|
| E001 | 输入为空 | "未检测到有效输入。请提供技能名称、任务描述或文件路径。" | 1. 补充输入内容 2. 重新发起请求 |
| E002 | 输入格式无法识别 | "无法识别输入格式。支持文本、文件路径和 URL。" | 1. 确认输入类型 2. 转换为支持的格式 3. 重试 |
| E003 | 无匹配结果 | "未找到与查询条件匹配的技能。请尝试更换关键词或扩大搜索范围。" | 1. 简化查询词 2. 使用更通用的分类标签 3. 重试 |
| E004 | URL 解析失败 | "无法从提供的 URL 中提取有效信息。请检查链接可访问性。" | 1. 确认 URL 可访问 2. 手动提供文本内容 3. 重试 |
| E005 | 批量处理中断 | "批量处理在第 N 条记录时中断。已处理部分已保存。" | 1. 检查第 N 条记录的格式 2. 修正后重新提交 3. 或跳过问题记录 |

---

## 六、FAQ 反模式：常见坑与对照

### 坑 1：把"推荐"当"保证"

- **错误做法**：认为推荐的技能一定适合所有场景
- **正确姿势**：将推荐视为起点，结合任务具体需求做二次筛选
- **反模式示例**：`"你推荐这个，那它肯定能处理我的数据"` → 应改为 `"这个技能在哪些场景下表现较好？"`

### 坑 2：忽略置信度标注

- **错误做法**：不看置信度，把低置信度结果当确定结果使用
- **正确姿势**：低置信度结果仅作参考，需人工核实关键字段
- **反模式示例**：`"它写了版本号，那肯定是对的"` → 应检查是否带 `[需核实:]` 标记

### 坑 3：混淆"技能目录"与"技能执行"

- **错误做法**：认为本 Skill 能直接运行其他技能
- **正确姿势**：本 Skill 只提供导航和装配建议，实际执行需在 Hermes Agent 环境中操作
- **反模式示例**：`"帮我用这个技能跑一下数据"` → 应改为 `"帮我找到能处理这个数据的技能，并告诉我怎么调用"`

### 坑 4：批量处理时不做数据清洗

- **错误做法**：直接提交含格式错误的批量数据
- **正确姿势**：先检查数据格式，确保每条记录包含必要字段
- **反模式示例**：`"我直接粘贴了 100 行，你看着办"` → 应提前确认字段完整性

### 坑 5：依赖单一触发词

- **错误做法**：只用一个固定词触发，换种说法就找不到
- **正确姿势**：使用同义场景词扩展触发范围
- **反模式示例**：`"我说'技能列表'它没反应"` → 可尝试"技能导航"、"技能目录"等变体

---

## 七、渐进式披露：分层次阅读路径

### 7.1 速查卡（30 秒上手）

```
┌─────────────────────────────────────────────┐
│  1. 输入任务描述或技能名称                     │
│  2. 获取匹配结果（表格/JSON）                 │
│  3. 检查置信度标注                            │
│  4. 有 [需核实:] 标记 → 人工确认              │
│  5. 无标记 → 按推荐使用                       │
└─────────────────────────────────────────────┘
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」章节，了解本 Skill 能做什么、不能做什么
2. 查看「触发方式」表格，确认自己的使用场景
3. 按「标准流程」执行一次完整操作
4. 遇到问题查「错误码体系」

### 7.3 进阶路径（熟练使用）

1. 掌握「置信度门控」规则，理解占位符含义
2. 熟悉「FAQ 反模式」，避免常见错误
3. 使用批量处理能力，结合自定义输出格式
4. 将本 Skill 与其他技能组合使用，形成工作流

---

## 八、参数配置参考

| 参数名 | 默认值 | 可选值 | 说明 |
|--------|--------|--------|------|
| output_format | markdown | markdown / json / csv | 输出格式 |
| max_results | 5 | 1-20 | 最大返回条数 |
| confidence_threshold | 0.6 | 0-1 | 置信度过滤阈值 |
| include_placeholder | true | true / false | 是否显示 [需核实:] 占位符 |
| sort_by | relevance | relevance / name / category | 排序方式 |

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。本 Skill 提供的所有信息、推荐和建议仅供参考，不构成任何形式的保证或承诺。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、反汇编或试图提取源代码。
3. **合规使用**：使用者应确保使用方式符合当地法律法规及 Hermes Agent 平台的相关规定。
4. **免责声明**：本 Skill 由 AI 辅助生成，可能存在信息不准确或不完整的情况。使用者应自行核实关键信息。

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*

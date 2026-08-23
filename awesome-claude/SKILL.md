---
slug: awesome-claude
name: awesome-claude
displayName: 资产检索分发 工作流盘点 批量处理
description: 检索分发 Claude 与 AI 工作流资产，支持结构化输出与批量处理。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: FlowForge Studio
agent_created: true
trigger_words: ["awesome-claude", "claude资产", "ai工作流", "mcp服务器", "技能检索", "资产盘点", "工作流目录", "工具清单"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

# Skill 文档：资产检索分发（awesome-claude）

## 一、能力边界速查卡

### 1.1 能做什么

| 能力项 | 说明 | 边界值 |
|--------|------|--------|
| 资产检索 | 从用户提供的 URL、文件或粘贴文本中提取 Claude 生态相关资产信息 | 单次输入文本 ≤ 50,000 字符 |
| 结构化输出 | 将资产信息整理为 Markdown 表格（默认）或 JSON 格式 | 单批输出 ≤ 100 条记录 |
| 字段补全 | 对缺失字段标注 `[需核实:字段名]` 占位符 | 推断置信度 > 30% 时必须先询问用户 |
| 批量处理 | 支持多来源资产合并去重后统一输出 | 去重键：`name + source_url` 组合 |

### 1.2 不能做什么

| 禁止项 | 说明 |
|--------|------|
| 不编造数据 | 无法从输入中确认的信息，一律输出占位符，不得虚构 |
| 不反向工程 | 不解析、不逆向任何第三方 Skill 的内部逻辑或提示词结构 |
| 不提供法律意见 | 涉及版权、许可合规问题时不作判断，仅提示用户自行核实 |
| 不执行代码 | 本 Skill 仅做信息检索与整理，不运行、不调试任何 MCP 服务器或脚本 |

### 1.3 适用对象

- 需要快速盘点团队内部 Claude 资产的使用者
- 正在调研 AI 工作流工具链的技术选型人员
- 维护个人 MCP 服务器清单的开发者
- 需要将资产信息导入下游表格或数据库的运营人员

---

## 二、触发方式与场景映射

### 2.1 触发词

以下任一词汇出现在用户输入中即触发本 Skill：

- `awesome-claude`
- `claude资产`
- `ai工作流`
- `mcp服务器`
- `技能检索`
- `资产盘点`
- `工作流目录`
- `工具清单`

### 2.2 场景映射表

| 用户说（大白话） | 实际意图 | 本 Skill 响应方式 |
|------------------|----------|-------------------|
| "帮我看看这个链接里有哪些 Claude 工具" | 从 URL 提取资产列表 | 抓取页面内容 → 提取资产 → 输出表格 |
| "我有一堆 MCP 服务器地址，整理一下" | 批量整理服务器清单 | 解析文本 → 去重 → 结构化输出 |
| "这个文件里的工作流帮我分类" | 文件内容分类整理 | 读取文件 → 按类型分组 → 输出分类结果 |
| "把上次的结果转成 JSON 给我" | 格式转换 | 重新处理输入 → 输出 JSON 格式 |

---

## 三、标准执行流程

### 3.1 前置条件

| 条件 | 要求 |
|------|------|
| 输入来源 | 至少提供以下一种：URL、文件路径、直接粘贴文本 |
| 输入格式 | 纯文本、Markdown、JSON、CSV 均可 |
| 环境要求 | 无特殊依赖，纯文本处理即可完成 |

### 3.2 执行步骤

**步骤 1：输入解析**

1. 识别输入类型（URL / 文件 / 文本）
2. 提取原始内容，去除无关格式
3. 若为 URL，抓取页面正文内容（仅限公开可访问页面）

**步骤 2：资产识别**

1. 扫描文本中与 Claude 生态相关的关键词（如 `claude`、`mcp`、`skill`、`workflow`、`agent`）
2. 提取候选资产条目，每条包含以下字段：

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `name` | string | 是 | 资产名称 |
| `type` | enum | 是 | `skill` / `mcp` / `workflow` / `agent` / `tool` |
| `source_url` | string | 否 | 来源链接 |
| `description` | string | 否 | 简短描述（≤ 200 字） |
| `tags` | array | 否 | 标签列表 |
| `confidence` | float | 是 | 提取置信度（0.0 - 1.0） |

**步骤 3：置信度评估**

1. 对每个字段计算提取置信度
2. 置信度 < 0.7 的字段标记为 `[需核实:字段名]`
3. 若某条记录的 `name` 字段置信度 < 0.3，整条记录标记为 `[需核实:整条记录]`

**步骤 4：去重与合并**

1. 以 `name + source_url` 为去重键
2. 重复记录保留置信度较高者
3. 合并相同资产的标签字段

**步骤 5：输出生成**

1. 默认输出 Markdown 表格，格式如下：

```markdown
| 序号 | 名称 | 类型 | 来源 | 描述 | 标签 | 置信度 |
|------|------|------|------|------|------|--------|
| 1 | example-skill | skill | https://... | 示例描述 | [tag1, tag2] | 0.92 |
```

2. 若用户指定 `--json` 参数，输出 JSON 数组格式：

```json
[
  {
    "name": "example-skill",
    "type": "skill",
    "source_url": "https://...",
    "description": "示例描述",
    "tags": ["tag1", "tag2"],
    "confidence": 0.92
  }
]
```

### 3.3 输出规范

| 项目 | 规范 |
|------|------|
| 输出格式 | Markdown 表格（默认）或 JSON（`--json` 参数） |
| 排序规则 | 按置信度降序排列 |
| 数量限制 | 单批最多 100 条，超出部分提示用户分批处理 |
| 占位符 | 缺失字段统一使用 `[需核实:字段名]` |
| 空结果 | 无匹配资产时输出："未找到符合条件的资产，请检查输入内容。" |

---

## 四、置信度门控机制

### 4.1 置信度分级

| 置信度范围 | 处理策略 |
|------------|----------|
| 0.9 - 1.0 | 直接输出，无需确认 |
| 0.7 - 0.9 | 正常输出，但标注"需人工复核" |
| 0.3 - 0.7 | 输出占位符 `[需核实:字段名]`，并在结果末尾附注说明 |
| < 0.3 | 不输出该字段，整条记录标记为 `[需核实:整条记录]` |

### 4.2 推断字段处理

当推断置信度 > 30% 时，**必须先询问用户**，不得直接输出推断结果。

**询问模板：**

> 检测到字段 `[字段名]` 无法从输入中直接确认，我推断其值为 `[推断值]`（置信度约 [百分比]%）。是否采用该推断值？请回复"采用"或提供正确值。

### 4.3 示例

**输入文本：**

```
这是一个名为 MyAgent 的工具，用于自动化测试。
```

**输出结果：**

| 序号 | 名称 | 类型 | 来源 | 描述 | 标签 | 置信度 |
|------|------|------|------|------|------|--------|
| 1 | MyAgent | agent | [需核实:source_url] | 用于自动化测试 | [需核实:tags] | 0.85 |

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 输入为空 | "未检测到有效输入，请提供 URL、文件路径或粘贴文本。" | 1. 检查输入是否为空 2. 重新提供输入内容 |
| E002 | 输入超限 | "输入内容超过 50,000 字符限制，请分段处理。" | 1. 将输入拆分为多个批次 2. 逐批提交处理 |
| E003 | URL 无法访问 | "无法访问该 URL，请确认链接有效且公开可访问。" | 1. 检查 URL 拼写 2. 确认页面未设置访问限制 3. 改用文本粘贴方式 |
| E004 | 无匹配资产 | "未找到符合条件的资产，请检查输入内容。" | 1. 确认输入包含 Claude 生态相关关键词 2. 扩大搜索范围 |
| E005 | 批量超限 | "单批最多处理 100 条记录，当前超出限制。" | 1. 减少输入规模 2. 分批处理 |
| E006 | 格式错误 | "无法解析输入格式，请确认为纯文本、Markdown、JSON 或 CSV。" | 1. 转换输入格式 2. 重新提交 |
| E007 | 置信度不足 | "多条记录置信度低于阈值，已标记为 [需核实] 占位符。" | 1. 查看标记字段 2. 补充确认信息 3. 重新处理 |

---

## 六、常见坑与反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|--------------------|----------|
| 编造缺失信息 | 对无法确认的字段随意填写猜测值 | 使用 `[需核实:字段名]` 占位符，并提示用户确认 |
| 忽略置信度门控 | 推断值直接输出，不询问用户 | 置信度 > 30% 的推断必须先行询问 |
| 超量处理 | 一次性处理超过 100 条记录 | 分批处理，每批 ≤ 100 条 |
| 混淆资产类型 | 将 MCP 服务器误标为 Skill | 严格按 `type` 枚举值分类：`skill` / `mcp` / `workflow` / `agent` / `tool` |
| 重复输出 | 同一资产在结果中出现多次 | 使用 `name + source_url` 去重键合并重复项 |
| 忽略来源标注 | 输出结果不包含来源链接 | 每条记录必须保留 `source_url` 字段（如缺失则标注占位符） |

---

## 七、渐进式披露路径

### 7.1 新手快速上手（5 分钟）

1. 阅读「能力边界速查卡」（第一节），了解能做什么、不能做什么
2. 查看「触发方式与场景映射」（第二节），确认如何激活技能
3. 按「标准执行流程」（第三节）操作一次，熟悉输入输出
4. 遇到问题查「错误码体系」（第五节）

### 7.2 进阶用户深化（30 分钟）

1. 理解「置信度门控机制」（第四节），掌握推断字段处理逻辑
2. 阅读「常见坑与反模式对照」（第六节），避免使用误区
3. 自定义输出格式，适配自己的下游工具链
4. 结合批量处理能力，构建自动化资产盘点流程

### 7.3 参数速查

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--json` | flag | 无 | 输出 JSON 格式 |
| `--selftest` | flag | 无 | 运行自检流程 |
| `--version` | flag | 无 | 显示版本信息 |
| `--batch-size` | int | 100 | 单批最大处理条数 |
| `--min-confidence` | float | 0.7 | 最低置信度阈值 |

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应确保输入内容不违反法律法规及平台政策，因输入内容引发的侵权、违规等问题由使用者自行承担全部责任。

2. **禁止反向工程**：使用者不得对本 Skill 的底层逻辑、提示词结构、评分机制进行反向工程、破解、提取或二次分发。

3. **服务变更**：本 Skill 可能随时更新或终止服务，恕不另行通知。

4. **无保证声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的保证，包括但不限于适销性、特定用途适用性和非侵权保证。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 FlowForge Studio

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*

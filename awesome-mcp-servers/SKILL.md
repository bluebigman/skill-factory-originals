---
slug: awesome-mcp-servers
name: awesome-mcp-servers
displayName: MCP服务器导航 能力速查 接入指引
description: 精选MCP服务器资源，结构化能力速查与接入指引。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: SkillForge Studio
agent_created: true
trigger_words: ["MCP服务器", "MCP资源", "服务器导航", "MCP能力速查", "MCP服务器列表", "MCP服务目录", "服务器检索", "MCP选型"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# MCP 服务器导航与能力速查

## 一、能力边界（一页纸速查卡）

### 1.1 本 Skill 能做什么

| 编号 | 能力项 | 说明 | 输出示例 |
|------|--------|------|----------|
| C1 | 输入解析 | 从用户提供的服务器名称与描述文本中提取关键信息 | 服务器名: `github-mcp-server` |
| C2 | 能力标签映射 | 将描述文本中的动词/名词短语映射到标准能力标签 | `代码托管`、`仓库管理`、`Issue追踪` |
| C3 | 结构化表格生成 | 按名称、描述、能力标签、置信度四列输出 Markdown 表格 | 见 3.3 节示例 |
| C4 | 置信度标注 | 对信息不完整的字段自动附加 `[需核实:字段名]` 占位符 | `[需核实:依赖环境]` |
| C5 | 格式定制 | 支持 `output_format=json`、`group_by=capability`、`detail_level=full` 三种参数 | 见 5.1 节 |

### 1.2 本 Skill 不能做什么

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不保证实时性 | 服务器列表基于训练数据快照，不反映最新发布状态 |
| L2 | 不做安全审计 | 不评估任何服务器的安全性、合规性或代码质量 |
| L3 | 不处理非文本输入 | 无法解析图片、音频、二进制文件中的服务器信息 |
| L4 | 不执行接入操作 | 仅提供信息整理与速查，不实际连接或配置任何 MCP 服务器 |
| L5 | 不处理超短描述 | 描述少于 10 个字符时直接报错（见错误码 E1001） |

### 1.3 适用对象

- **MCP 服务使用者**：需要快速了解某个 MCP 服务器能提供什么能力。
- **技术选型人员**：在多个 MCP 服务器之间做对比筛选。
- **自动化流程集成者**：需要将服务器信息以 JSON 格式接入下游系统。

---

## 二、触发方式

### 2.1 触发词速查

| 触发场景 | 用户可能说的话 | 触发词匹配 |
|----------|----------------|------------|
| 查询服务器列表 | "帮我看看有哪些 MCP 服务器" | MCP服务器、MCP服务器列表 |
| 查询特定服务器 | "这个 MCP 服务器是干什么的？" | MCP能力速查、MCP资源 |
| 导航检索 | "有没有做数据库连接的 MCP？" | 服务器导航、MCP服务目录 |
| 选型对比 | "这几个服务器哪个适合做文件操作？" | MCP选型、服务器检索 |

### 2.2 大白话场景映射

| 用户意图（口语化） | Skill 内部动作 |
|--------------------|----------------|
| "这个工具是干嘛的？" | 解析描述 → 提取能力标签 → 输出单行速查 |
| "帮我整理一份清单" | 批量解析 → 生成完整表格 → 标注置信度 |
| "我要 JSON 格式的" | 设置 `output_format=json` → 输出结构化数据 |
| "按功能分类看看" | 设置 `group_by=capability` → 按能力分组输出 |

---

## 三、标准流程

### 3.1 前置条件

| 条件项 | 要求 | 不满足时的处理 |
|--------|------|----------------|
| 输入格式 | 纯文本（支持 Markdown 源码） | 报错 E2001 |
| 描述长度 | 每条描述 ≥ 10 个字符 | 报错 E1001 |
| 输入数量 | 单次最多 50 条服务器记录 | 超出部分截断并提示 |
| 必填字段 | 至少包含服务器名称 | 缺失时以 `[未命名服务器]` 占位 |

### 3.2 执行步骤（分步编号）

**Step 1：输入解析**
- 将输入文本按空行或分隔符拆分为多条记录。
- 每条记录提取 `name`（服务器名）和 `description`（描述文本）。
- 若输入为 JSON 数组，直接解析 `name` 与 `description` 字段。

**Step 2：能力标签匹配**
- 对每条描述执行关键词扫描，匹配标准能力标签表（见 3.4）。
- 每个描述最多提取 5 个能力标签，按匹配优先级排序。
- 若匹配标签数为 0，标记为 `[需核实:能力标签]`。

**Step 3：结构化整理**
- 生成四列表格：`服务器名称` | `描述摘要` | `能力标签` | `置信度`。
- 描述摘要截取前 80 个字符，超出部分以 `...` 省略。

**Step 4：置信度标注**
- 置信度分为三档：`高`（描述完整且标签匹配 ≥ 3 个）、`中`（描述完整但标签匹配 1-2 个）、`低`（描述不完整或标签匹配 0 个）。
- 低置信度记录在对应字段追加 `[需核实:字段名]` 占位符。

**Step 5：输出结果**
- 默认输出 Markdown 表格。
- 支持参数：`output_format`、`group_by`、`detail_level`（见 5.1 节）。

### 3.3 输出规范（示例）

```markdown
| 服务器名称 | 描述摘要 | 能力标签 | 置信度 |
|------------|----------|----------|--------|
| github-mcp-server | GitHub 官方 MCP 服务器，支持仓库管理、Issue 追踪、PR 操作... | 代码托管, 仓库管理, Issue追踪 | 高 |
| sqlite-mcp-server | 提供 SQLite 数据库读写能力，支持查询与事务操作 | 数据库, SQL查询 | 中 |
| unknown-server | 描述信息不足 | [需核实:能力标签] | 低 |
```

### 3.4 标准能力标签表

| 标签名 | 匹配关键词（示例） |
|--------|---------------------|
| 代码托管 | git, repository, repo, 仓库 |
| 文件操作 | file, filesystem, 文件, 读写 |
| 数据库 | database, sql, sqlite, mysql, 数据库 |
| API集成 | api, rest, graphql, 接口 |
| 消息通知 | notify, message, 通知, 推送 |
| 搜索检索 | search, query, 搜索, 检索 |
| 数据处理 | transform, pipeline, 处理, 转换 |
| 监控运维 | monitor, log, 监控, 日志 |
| 安全认证 | auth, token, 认证, 权限 |
| 其他 | 无法匹配时使用此标签 |

---

## 四、置信度门控

### 4.1 门控规则

| 场景 | 处理方式 |
|------|----------|
| 描述长度 < 10 字符 | 直接报错 E1001，不输出占位 |
| 描述完整但无标签匹配 | 输出 `[需核实:能力标签]` |
| 描述中缺少依赖环境信息 | 输出 `[需核实:依赖环境]` |
| 描述中缺少版本信息 | 输出 `[需核实:版本]` |
| 描述中缺少安全说明 | 输出 `[需核实:安全说明]` |

### 4.2 门控原则

- **不编造**：任何未在输入文本中明确出现的信息，一律以占位符标注。
- **可追溯**：每个占位符对应一个明确的字段名，便于用户定向补充。
- **可配置**：通过 `confidence_threshold` 参数（默认 0.5）控制是否输出低置信度记录。

---

## 五、进阶用法

### 5.1 参数配置表

| 参数名 | 类型 | 默认值 | 可选值 | 说明 |
|--------|------|--------|--------|------|
| `output_format` | string | `markdown` | `markdown` / `json` | 输出格式 |
| `group_by` | string | 无 | `capability` / `none` | 按能力分组输出 |
| `detail_level` | string | `standard` | `standard` / `full` | 是否输出依赖关系、环境变量等完整信息 |
| `confidence_threshold` | float | `0.5` | `0.0` - `1.0` | 置信度过滤阈值 |

### 5.2 参数组合示例

```bash
# 输出 JSON 格式，按能力分组，完整信息
output_format=json group_by=capability detail_level=full

# 只输出高置信度记录
confidence_threshold=0.8
```

### 5.3 完整信息模式（detail_level=full）

在标准四列基础上，额外输出以下字段（若输入中可提取）：

| 字段名 | 说明 | 缺失时占位 |
|--------|------|------------|
| 依赖环境 | 运行所需的 Node/Python/Go 等环境 | `[需核实:依赖环境]` |
| 版本要求 | 协议版本或服务器版本 | `[需核实:版本]` |
| 安全说明 | 认证方式、权限要求 | `[需核实:安全说明]` |
| 配置参数 | 环境变量或初始化参数 | `[需核实:配置参数]` |

---

## 六、错误码体系

| 错误码 | 错误场景 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E1001 | 描述少于 10 个字符 | "描述信息过短，无法提取有效能力标签" | 补充完整描述后重试 |
| E1002 | 输入为空 | "未检测到任何输入内容" | 检查输入是否为空或格式错误 |
| E2001 | 输入格式无法解析（非文本） | "仅支持纯文本或 JSON 格式输入" | 将输入转换为文本格式 |
| E2002 | 输入超过 50 条记录 | "单次最多处理 50 条记录，已截断超出部分" | 分批处理或减少输入量 |
| E3001 | 参数值非法 | "参数 `output_format` 仅支持 markdown 或 json" | 检查参数拼写与取值 |
| E3002 | 参数组合冲突 | "`group_by=capability` 与 `output_format=json` 不兼容" | 移除冲突参数或调整组合 |

---

## 七、FAQ 反模式对照

### 7.1 常见坑与反模式

| 编号 | 常见坑（反模式） | 正确做法 |
|------|------------------|----------|
| F1 | 输入描述过于笼统，如"一个 MCP 服务器" | 提供至少包含功能动词的完整描述，如"提供文件读写与目录遍历能力的 MCP 服务器" |
| F2 | 期望 Skill 验证服务器安全性 | 本 Skill 不执行安全审计，请自行查阅官方文档或运行测试 |
| F3 | 将 Skill 输出当作实时数据 | 输出基于训练数据快照，最新状态请以官方仓库为准 |
| F4 | 忽略置信度标注直接使用 | 对标注 `[需核实]` 的字段，务必人工复核后再做决策 |
| F5 | 一次性输入超过 50 条记录 | 分批输入，或使用脚本循环调用 |

### 7.2 反模式对照表

| 反模式描述 | 后果 | 替代方案 |
|------------|------|----------|
| 使用绝对化表述（如"这个服务器绝对安全"） | 误导决策 | 仅陈述事实，不做价值判断 |
| 编造不存在的字段信息 | 数据污染 | 使用 `[需核实]` 占位符 |
| 忽略错误码直接重试 | 浪费资源 | 先阅读错误码提示，修正输入后重试 |

---

## 八、渐进式披露

### 8.1 速查卡（30 秒上手）

1. 直接粘贴服务器名称和描述文本。
2. 说"MCP服务器"或"服务器导航"触发。
3. 查看 Markdown 表格，关注置信度标注。
4. 信息不全时，补充描述后重试。

### 8.2 新手路径（5 分钟）

1. 阅读「一、能力边界」了解能做什么、不能做什么。
2. 按「三、标准流程」的 Step 1-5 走一遍完整流程。
3. 遇到错误时对照「六、错误码体系」修正输入。
4. 阅读「七、FAQ 反模式对照」避免常见坑。

### 8.3 进阶路径（15 分钟）

1. 掌握「五、进阶用法」中的参数配置，对接自动化流程。
2. 理解「四、置信度门控」的规则，建立人工复核机制。
3. 结合 `detail_level=full` 获取完整信息，用于技术选型。
4. 参考「七、FAQ 反模式」优化输入质量，减少二次确认。

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的信息整理与速查功能仅供参考，不构成任何形式的保证或承诺。

2. **禁止反向工程**：禁止对本 Skill 进行反向工程、反编译、破解或试图提取底层算法。

3. **合规使用**：使用者应确保使用本 Skill 的行为符合当地法律法规及所在组织的合规要求。

4. **免责声明**：本 Skill 输出的服务器信息基于训练数据，不保证与最新状态一致。接入任何 MCP 服务器前，请自行评估其安全性、合规性与兼容性。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 SkillForge Studio

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

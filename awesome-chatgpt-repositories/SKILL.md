---
slug: awesome-chatgpt-repositories
name: awesome-chatgpt-repositories
displayName: 开源仓库检索 结构化整理 清单生成
description: 解析GitHub仓库文本，提取结构化字段，输出可筛选排序的清单表格。
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
trigger_words: ["awesome-chatgpt-repositories", "ChatGPT仓库", "开源项目检索", "OpenAI仓库", "Codex项目", "仓库清单整理", "GitHub项目列表"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 开源仓库清单整理助手（SKILL.md）

## 一、能力边界：一页纸速查卡

本 Skill 专注于将非结构化的 GitHub 仓库文本，转换为结构化的清单表格或数据文件。它不执行代码分析、不访问网络、不验证仓库实时状态。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入 | 用户粘贴的仓库列表文本、文件内容 | 直接读取本地文件路径（需用户粘贴内容） |
| 解析 | 识别仓库名、描述、Star 数、语言、链接等字段 | 解析非文本格式（图片、PDF 扫描件） |
| 处理 | 字段提取、过滤、排序、去重、格式转换 | 实时抓取 GitHub 数据、验证仓库是否仍存在 |
| 输出 | Markdown 表格、JSON、CSV | 生成图表、创建 PR、自动发布 |
| 适用对象 | 开发者、技术调研者、开源爱好者 | 需要实时数据监控的场景 |

**适用场景**：整理收藏夹、批量调研竞品仓库、生成周报附件、构建内部工具的数据源。

---

## 二、触发方式：场景映射表

当对话中出现以下意图时，本 Skill 自动激活：

| 用户可能说的话 | 触发词匹配 | 实际行为 |
|---------------|-----------|---------|
| "帮我整理一下这些仓库" | 仓库清单整理 | 解析文本 → 输出表格 |
| "把这段 GitHub 列表结构化" | 开源项目检索 | 提取字段 → 排序输出 |
| "过滤出 Python 的，Star 过千的" | 过滤语法 | 应用过滤条件 → 输出子集 |
| "输出成 JSON 给我" | 输出格式指定 | 转换格式 → 输出 JSON |
| "这是两份列表，合并一下" | 批量合并 | 合并去重 → 输出汇总表 |

**大白话示例**：
- "我贴一段 awesome 列表，你帮我弄成表格" → 直接解析输出
- "只要 Go 语言的，Star 从高到低排" → 过滤 + 排序
- "转成 CSV 我要导入 Excel" → 格式转换

---

## 三、标准流程：从输入到输出

### 前置条件
- 用户提供至少一条仓库记录文本（包含仓库名或 URL）
- 文本格式不限，但需可被正则识别（见下方字段提取规则）

### 执行步骤

**步骤 1：接收输入**
- 获取用户粘贴的文本或指定文件内容
- 若输入为空，提示："请提供需要整理的仓库列表文本"

**步骤 2：文本解析**
- 按行或按分隔符切分文本，识别仓库条目
- 典型条目格式示例：
  ```
  [owner/repo](https://github.com/owner/repo) - 描述文字。 Stars: 1234, Language: Python
  ```
  或纯文本：
  ```
  owner/repo - 描述。 1234 stars, Python
  ```

**步骤 3：字段提取**

| 字段名 | 提取规则 | 示例 | 缺失处理 |
|--------|---------|------|---------|
| `name` | 匹配 `owner/repo` 模式 | `openai/gpt-3` | 跳过该条 |
| `url` | 匹配 `github.com/owner/repo` | `https://github.com/openai/gpt-3` | 由 name 拼接 |
| `description` | 提取 `-` 或 `:` 后的文本，截断至 200 字符 | `GPT-3 的 API 封装库` | 置空 |
| `stars` | 匹配数字 + `stars`/`star`/`★` | `1234` | 置 0 |
| `language` | 匹配 `Language:` 或 `语言:` 后的字段 | `Python` | 置 `unknown` |
| `license` | 匹配 `License:` 或 `许可:` 后的字段 | `MIT` | 置 `unknown` |
| `last_updated` | 匹配日期格式 `YYYY-MM-DD` | `2024-01-15` | 置空 |

**步骤 4：应用过滤（可选）**
- 语法：`过滤: 字段=值, 字段>=值, 字段<=值`
- 支持字段：`language`, `stars`, `license`, `name`（支持 `*` 通配符）
- 示例：`过滤: language=Python, stars>=1000`
- 多个条件为 AND 关系

**步骤 5：排序与去重**
- 默认按 `stars` 降序排列
- 多份输入合并时，按 `name` 字段去重（保留 Star 数高的记录）
- 排序规则：`stars` 为数字比较，`name` 为字典序

**步骤 6：生成输出**
- 默认输出 Markdown 表格，列顺序：`name | stars | language | license | description | url`
- 可选格式：`JSON`（数组对象）、`CSV`（逗号分隔，含表头）
- 输出前自动统计：`共 N 条记录，M 条被过滤`

### 输出规范

**Markdown 表格示例**：

| name | stars | language | license | description | url |
|------|-------|----------|---------|-------------|-----|
| openai/gpt-3 | 45200 | Python | MIT | GPT-3 API 封装库 | https://github.com/openai/gpt-3 |
| microsoft/Codex | 23100 | Rust | Apache-2.0 | Codex CLI 工具 | https://github.com/microsoft/Codex |

**JSON 输出示例**：
```json
[
  {
    "name": "openai/gpt-3",
    "stars": 45200,
    "language": "Python",
    "license": "MIT",
    "description": "GPT-3 API 封装库",
    "url": "https://github.com/openai/gpt-3"
  }
]
```

---

## 四、置信度门控：不编造原则

当提取的字段存在以下情况时，使用占位符而非猜测：

| 情况 | 输出占位符 | 说明 |
|------|-----------|------|
| 描述文本缺失 | `[需核实:description]` | 不自动生成描述 |
| 语言无法识别 | `[需核实:language]` | 不猜测语言类型 |
| Star 数格式异常 | `[需核实:stars]` | 不估算数值 |
| 许可证信息缺失 | `[需核实:license]` | 不假设默认许可证 |
| URL 无法从 name 拼接 | `[需核实:url]` | 不构造可能错误的链接 |

**门控逻辑**：
- 若一条记录中 `name` 字段缺失，整条记录跳过并在输出末尾标注："已跳过 N 条无法识别的记录"
- 若某字段提取置信度低于 80%（如描述含混合语言），使用占位符
- 用户可随时要求"补充核实"，Skill 会列出所有占位符字段

---

## 五、错误码体系：问题定位与修复

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|---------|---------|---------|
| E001 | 输入为空 | "未检测到任何文本，请粘贴仓库列表" | 检查输入是否为空，重新粘贴 |
| E002 | 无法识别仓库名 | "第 3 行未找到 owner/repo 格式" | 确认文本包含 GitHub 仓库路径 |
| E003 | 过滤条件语法错误 | "过滤条件格式应为 字段=值 或 字段>=值" | 检查过滤语法，参考步骤 4 |
| E004 | 输出格式不支持 | "仅支持 markdown/json/csv 三种格式" | 重新指定格式 |
| E005 | 字段提取冲突 | "第 5 条记录的 stars 字段存在两种格式" | 手动指定优先格式，或忽略冲突字段 |
| E006 | 合并去重异常 | "检测到重复记录但 Star 数差异过大" | 保留较高 Star 数，并提示用户确认 |

**错误处理流程**：
1. 检测到错误 → 输出错误码 + 具体位置
2. 给出修正建议 → 用户调整输入或指令
3. 重试 → 重新执行解析流程

---

## 六、FAQ 反模式：常见坑与规避

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|---------|
| 描述含换行 | 直接截断导致表格断裂 | 将换行替换为空格，再截断 |
| Star 数带千分位逗号 | 直接转数字失败 | 先移除逗号再解析（如 `1,234` → `1234`） |
| 语言字段多值 | 只取第一个值 | 用 `/` 分隔多个语言，如 `Python/JavaScript` |
| 仓库名大小写混淆 | 直接去重导致误判 | 统一转为小写后再比较去重 |
| 输入含无关文本 | 将广告语误认为仓库描述 | 仅提取 `-` 或 `:` 后的首个句子 |

**反模式对照**：
- ❌ "这个仓库很火" → 不提取为描述
- ✅ "openai/gpt-3 - 一个强大的 API 库" → 提取 `一个强大的 API 库`
- ❌ 将 `stars: 1.2k` 解析为 `1.2`
- ✅ 将 `1.2k` 转换为 `1200`

---

## 七、渐进式披露：分层次阅读路径

### 速查卡（30 秒上手）
1. 粘贴仓库文本 → 2. 发送"整理一下" → 3. 获得表格
4. 可选：加过滤条件 → 5. 可选：指定输出格式

### 新手路径（5 分钟掌握）
- 阅读「能力边界」了解适用范围
- 阅读「标准流程」步骤 1-3 理解基本操作
- 尝试一次完整输入输出

### 进阶路径（深度使用）
- 掌握「字段提取规则」中的边界情况
- 组合使用过滤、排序、去重功能
- 对接外部工具链（通过 JSON/CSV 输出）
- 理解「置信度门控」确保数据质量

### 专家路径（自定义扩展）
- 修改提取正则表达式（需自行维护）
- 增加自定义字段（如 `topics`、`homepage`）
- 集成到 CI/CD 流水线中自动生成周报

---

## 八、参数速查表

| 参数 | 默认值 | 可选值 | 说明 |
|------|--------|--------|------|
| `format` | `markdown` | `markdown` / `json` / `csv` | 输出格式 |
| `sort_by` | `stars` | `stars` / `name` / `last_updated` | 排序字段 |
| `sort_order` | `desc` | `asc` / `desc` | 排序方向 |
| `dedup` | `true` | `true` / `false` | 是否去重 |
| `max_records` | 无限制 | 任意正整数 | 最大输出条数 |
| `include_fields` | 全部 | 字段名子集 | 控制输出列 |

**使用示例**：
- `输出: json, sort_by=name, max_records=20`
- `过滤: language=Go, stars>=5000, 输出: csv`

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。包括但不限于因输出数据不准确、信息遗漏或格式错误导致的任何直接或间接损失。
2. **禁止反向工程**：不得对本 Skill 的提示词、逻辑、生成机制或底层设计意图进行反向工程、破解、提取或二次分发。
3. **数据验证**：本 Skill 输出的结构化数据基于用户提供的输入文本，不保证与 GitHub 实时数据一致。使用者应自行验证关键信息。
4. **合规使用**：使用者应确保输入文本的获取和传播符合相关法律法规及 GitHub 服务条款。

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*

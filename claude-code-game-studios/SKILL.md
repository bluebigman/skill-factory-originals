---
slug: claude-code-game-studios
name: claude-code-game-studios
displayName: 游戏数据转换 批量结构化 工坊
description: 将游戏相关数据、文件或URL转换为结构化结果，支持批量处理与自定义格式。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨工坊
agent_created: true
trigger_words: ["claude code game studios", "游戏工坊", "游戏数据转换", "结构化输出", "批量处理", "游戏数据整理", "批量格式化"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 游戏数据转换工坊（Game Studios）

## 一、能力边界速查卡

| 维度 | 说明 |
|------|------|
| **能做什么** | 将游戏相关数据（JSON、CSV、TXT、URL 指向的公开数据）转换为结构化结果；支持批量处理；支持自定义输出格式（如 Markdown 表格、JSON Schema、CSV 等） |
| **不能做什么** | 不能访问需登录/付费墙后的数据；不能解析加密或二进制游戏存档；不能对图片/音频内容做语义理解；不能保证数据源本身的准确性 |
| **适用对象** | 游戏策划、数据分析师、社区运营、独立开发者、游戏评测作者 |
| **不适用对象** | 需要实时游戏内数据抓取（需专用 API）；需要法律效力的数据报告；需要处理超过 500 个文件的超大批量任务（建议分批） |

**输入要求**：文件编码建议 UTF-8（无 BOM）；单个文件大小建议 ≤ 5MB；URL 需为公开可访问地址。

---

## 二、触发方式与场景映射

| 触发词/短语 | 典型场景 |
|-------------|----------|
| "claude code game studios" | 直接调用本工坊的完整流程 |
| "游戏工坊" | 中文场景下的快捷入口 |
| "游戏数据转换" | 需要将非结构化数据转为结构化格式 |
| "结构化输出" | 需要统一字段、统一格式的输出 |
| "批量处理" | 多个文件需要按同一规则处理 |
| "游戏数据整理" | 对散乱数据进行清洗、归类、格式化 |

**大白话示例**：
- "帮我把这个文件夹里 20 个游戏角色 JSON 统一转成表格"
- "这个 URL 里的游戏排行榜数据，整理成 Markdown 表格"
- "我有 3 个 CSV 文件，字段不一样，帮我统一格式"

---

## 三、标准操作流程

### 前置条件（必须满足）

1. 所有待处理文件已放入同一目录（或提供可访问的 URL 列表）
2. 文件命名规范一致（如 `game_01.json`、`game_02.json`）
3. 已明确输出格式（默认输出 Markdown 表格；可选 JSON / CSV）
4. 已确认数据源无版权争议（仅处理你有权使用的数据）

### 执行步骤

**第一步：输入确认**
- 列出所有待处理文件路径或 URL
- 确认文件数量、类型、大小
- 确认输出格式与目标目录

**第二步：单样本试运行**
- 选取 1 个代表性文件执行转换
- 核对输出字段是否完整、格式是否正确
- 如有问题，调整字段映射规则后重试

**第三步：批量执行**
- 对全量数据执行转换
- 输出文件命名规则：`原文件名_structured.扩展名`
- 原始文件不做任何修改（只读操作）

**第四步：结果校验**
- 抽查至少 10% 的输出条目
- 核对关键字段（如名称、数值、日期）与源数据一致
- 检查是否有缺失字段或异常值

### 输出规范

| 输出格式 | 默认结构 | 示例 |
|----------|----------|------|
| Markdown 表格 | `\| 字段名 \| 字段名 \|` + 分隔行 + 数据行 | `\| 角色名 \| 等级 \| 职业 \|` |
| JSON | 数组对象，键名与源数据字段映射 | `[{"name":"A","level":10}]` |
| CSV | 首行为表头，后续为数据行 | `角色名,等级,职业` |

**自定义格式**：可在输入时附加说明，如"输出为 YAML 格式，字段顺序为 name, level, class"。

---

## 四、置信度门控

当遇到以下情况时，**不编造数据**，输出占位符：

| 情况 | 处理方式 |
|------|----------|
| 源数据字段缺失 | 输出 `[需核实:字段名]` |
| 数值明显异常（如等级为负数） | 输出 `[需核实:数值]` 并保留原值 |
| URL 无法访问 | 跳过该条目，在结果末尾标注 `[需核实:URL不可访问]` |
| 文件编码无法识别 | 输出 `[需核实:文件编码]` 并跳过该文件 |

**原则**：宁可标注缺失，不猜测填充。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 文件不存在 | "未找到指定文件，请检查路径" | 确认路径拼写；检查文件是否被移动 |
| `E002` | 文件格式不支持 | "仅支持 JSON/CSV/TXT/公开 URL" | 转换文件格式后重试 |
| `E003` | 字段映射冲突 | "源数据字段与目标字段存在冲突" | 检查字段名是否重复；调整映射规则 |
| `E004` | 批量处理中断 | "批量处理在第 N 个文件处中断" | 查看错误日志；修复后从第 N 个文件继续 |
| `E005` | 输出目录无写入权限 | "无法写入输出目录" | 更换输出目录；检查权限设置 |
| `E006` | 数据量超出单次限制 | "单次处理建议不超过 500 个文件" | 分批处理；或压缩文件体积 |

---

## 六、FAQ 与反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 文件命名混乱 | 直接批量处理，不检查命名 | 先统一命名规范，再执行批量 |
| 字段理解偏差 | 凭猜测映射字段 | 先试运行 1 个样本，确认映射正确 |
| 数据源不可靠 | 直接信任源数据 | 抽查关键字段，标注异常值 |
| 输出格式不匹配 | 不指定格式，用默认输出 | 明确告知所需格式与字段顺序 |
| 忽略原始备份 | 直接修改原文件 | 只读操作，输出到新文件 |

**反模式示例**：
- ❌ "把所有文件都转了吧，不用检查" → 先试运行 1 个
- ❌ "这个字段应该是等级，直接填 10" → 源数据没有就标 `[需核实:等级]`
- ❌ "输出成什么都行" → 必须明确格式，否则默认 Markdown 表格

---

## 七、渐进式披露路径

### 速查卡（30 秒上手）

```
1. 放文件 → 2. 说"游戏工坊" → 3. 指定输出格式 → 4. 试运行 1 个 → 5. 批量执行 → 6. 抽查结果
```

### 新手路径（首次使用）

1. 阅读「能力边界速查卡」确认适用场景
2. 准备 1 个测试文件，执行「单样本试运行」
3. 对照「输出规范」检查结果
4. 确认无误后，再执行批量处理

### 进阶路径（熟练用户）

1. 自定义字段映射规则（输入时附加说明）
2. 使用错误码快速定位问题
3. 结合「置信度门控」处理不完整数据
4. 对输出结果进行二次清洗（如去重、排序）

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 仅提供数据处理辅助，不构成任何形式的数据准确性保证或法律意见。
2. **数据合规**：使用者须确保所处理的数据来源合法、有权使用。因数据版权、隐私等问题引发的纠纷，由使用者自行解决。
3. **禁止反向工程**：不得对本 Skill 的提示词结构、内部逻辑进行反向工程、破解、提取或用于训练竞争性模型。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性。
5. **修改与终止**：作者保留随时修改、更新或终止本 Skill 的权利，恕不另行通知。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 林墨工坊

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

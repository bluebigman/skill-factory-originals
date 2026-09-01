---
slug: awesome-design-skills
name: awesome-design-skills
displayName: 设计技能 选型比对 集成参考
description: 检索比对67个设计技能文件，辅助选型与集成参考。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 灵感设计工坊
agent_created: true
trigger_words: ["awesome-design-skills", "design skill", "设计技能", "skill 文件", "DESIGN.md", "技能比对", "技能选型", "技能评估"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# awesome-design-skills — 设计技能文件检索与比对助手

## 一、能力边界（一页纸速查卡）

### 1.1 本技能能做什么

| 能力项 | 说明 | 输入要求 | 输出形式 |
|--------|------|----------|----------|
| 字段清单提取 | 从 DESIGN.md 中提取结构化字段 | 粘贴 1 个文件内容 | 字段清单（Markdown 列表） |
| 完整度评分 | 按字段覆盖率计算百分比 | 同上 | 百分比数值 + 缺失项标注 |
| 多文件比对 | 横向对比 2-5 个技能文件 | 粘贴 2-5 个文件内容 | 对比表格（Markdown） |
| 集成建议 | 基于输入输出格式匹配度给出参考 | 对比结果 + 使用场景描述 | 建议列表 |

### 1.2 本技能不能做什么

- **不能解析文件路径**：仅接受粘贴的文本内容，不接受本地文件路径或 URL。
- **不能自动抓取网络资源**：不联网检索，仅处理用户提供的内容。
- **不能保证文件质量**：评分仅反映字段完整度，不评估设计逻辑优劣。
- **不能替代人工决策**：集成建议仅供参考，最终选择需人工复核。
- **不能处理超过 5 个文件**：单批次上限为 5 个，超出需分批。

### 1.3 适用对象

- 需要从多个设计技能文件中选型的开发者
- 需要评估技能文件完整度的技术负责人
- 需要标准化技能文件格式的团队管理者

---

## 二、触发方式

### 2.1 触发词

以下任一词汇或短语可激活本技能：

- `awesome-design-skills`
- `design skill`
- `设计技能`
- `skill 文件`
- `DESIGN.md`
- `技能比对`
- `技能选型`
- `技能评估`

### 2.2 场景映射表

| 用户说（大白话） | 本技能理解 | 执行动作 |
|------------------|------------|----------|
| "帮我看看这个技能文件全不全" | 评估单个文件字段完整度 | 提取字段 → 评分 → 输出缺失项 |
| "这两个设计技能哪个更适合我们" | 多文件比对 | 提取字段 → 对比 → 输出差异表 |
| "我想知道这个技能能不能做XX" | 能力边界判断 | 读取能力描述字段 → 输出判断 |
| "帮我整理一下这几个技能的输入输出" | 格式匹配分析 | 提取输入输出字段 → 输出对照表 |

---

## 三、标准流程

### 3.1 前置条件

- 已获取 DESIGN.md 文件内容（复制粘贴到对话中）
- 文件数量：1-5 个
- 文件格式：Markdown 或纯文本

### 3.2 执行步骤

**步骤 1：输入确认**

确认用户提供的文件数量与内容完整性。若内容不完整（如截断），提示用户重新提供。

**步骤 2：单文件评估（先单后多）**

对每个文件依次执行：

1. 提取字段清单（见 3.3 字段提取规则）
2. 计算完整度评分（见 3.4 评分标准）
3. 标注缺失字段与 `[需核实]` 字段

**步骤 3：多文件比对（可选）**

若用户提供 2-5 个文件，生成对比表格：

- 行：字段名称
- 列：文件编号（文件1、文件2...）
- 单元格：字段值摘要或 `缺失` / `[需核实]`

**步骤 4：输出集成建议（可选）**

根据用户描述的使用场景，结合比对结果给出建议：

- 字段完整度高的文件优先考虑
- 输入输出格式匹配度高的文件优先考虑
- 标注 `[需核实]` 的字段需用户补充确认

### 3.3 字段提取规则

| 字段类别 | 字段名 | 提取规则 |
|----------|--------|----------|
| 基础信息 | slug | 取 `slug:` 后的值 |
| 基础信息 | name | 取 `name:` 后的值 |
| 基础信息 | description | 取 `description:` 后的值 |
| 基础信息 | version | 取 `version:` 后的值 |
| 基础信息 | license | 取 `license:` 后的值 |
| 能力描述 | capability_outline | 取 `capability_outline:` 后的列表 |
| 接口定义 | cli_interface | 取 `cli_interface:` 后的列表 |
| 使用流程 | usage_steps | 取 `usage_steps:` 后的列表 |
| 进阶用法 | advanced_usage | 取 `advanced_usage:` 后的列表 |
| 最佳实践 | best_practices | 取 `best_practices:` 后的列表 |
| 合规条款 | compliance | 取 `compliance:` 后的列表 |

### 3.4 评分标准

完整度评分 = （已提取字段数 ÷ 应提取字段总数）× 100%

应提取字段总数 = 11（上述 11 个字段类别）

评分等级：

| 评分区间 | 等级 | 说明 |
|----------|------|------|
| 90%-100% | 优秀 | 字段齐全，可直接参考 |
| 70%-89% | 良好 | 大部分字段存在，少量缺失 |
| 50%-69% | 一般 | 关键字段存在，但缺失较多 |
| 0%-49% | 不足 | 字段严重缺失，不建议参考 |

### 3.5 输出规范

**单文件评估输出格式：**

```
## 文件评估报告

### 文件标识
- 文件编号：文件1
- slug：xxx
- name：xxx

### 字段清单
| 字段类别 | 字段名 | 状态 | 值摘要 |
|----------|--------|------|--------|
| 基础信息 | slug | ✅ | xxx |
| 基础信息 | name | ✅ | xxx |
| ... | ... | ... | ... |

### 完整度评分
- 得分：82%（9/11）
- 缺失字段：capability_outline、compliance
- 需核实字段：usage_steps（内容不完整）

### 缺失项说明
- capability_outline：未找到该字段，建议补充能力描述
- compliance：未找到该字段，建议补充合规条款
```

**多文件比对输出格式：**

```
## 多文件比对报告

### 文件清单
| 编号 | slug | name | 完整度 |
|------|------|------|--------|
| 文件1 | xxx | xxx | 82% |
| 文件2 | xxx | xxx | 91% |

### 字段对比表
| 字段名 | 文件1 | 文件2 |
|--------|-------|-------|
| slug | xxx | xxx |
| name | xxx | xxx |
| description | xxx | xxx |
| ... | ... | ... |

### 集成建议
- 文件2 字段完整度更高，建议优先参考
- 文件1 的 usage_steps 需核实，建议补充后再评估
```

---

## 四、置信度门控

### 4.1 基本原则

本技能**不编造信息**。当遇到以下情况时，输出 `[需核实:字段名]` 占位符：

- 字段内容不完整（如截断、缺失关键信息）
- 字段格式不符合预期（如非标准 YAML 格式）
- 字段值存在歧义（如多个可能值）

### 4.2 占位符使用示例

| 场景 | 输出 |
|------|------|
| description 字段内容不完整 | `[需核实:description]` |
| capability_outline 格式异常 | `[需核实:capability_outline]` |
| version 值无法解析 | `[需核实:version]` |

### 4.3 用户补充机制

当输出包含 `[需核实]` 字段时，提示用户：

> 检测到以下字段需核实：xxx。请提供补充信息，或确认忽略该字段。

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 输入为空 | "未检测到文件内容，请粘贴 DESIGN.md 内容。" | 1. 复制文件内容 2. 粘贴到对话中 3. 重新发起请求 |
| E002 | 文件数量超限 | "文件数量超过 5 个，请分批处理。" | 1. 将文件分为多批 2. 每批不超过 5 个 3. 逐批提交 |
| E003 | 内容格式异常 | "文件内容格式不符合预期，请检查是否为 Markdown 或纯文本。" | 1. 确认文件格式 2. 转换为纯文本 3. 重新提交 |
| E004 | 字段提取失败 | "无法从内容中提取有效字段，请确认文件包含标准字段定义。" | 1. 检查文件头部 frontmatter 2. 确认字段名称正确 3. 重新提交 |
| E005 | 评分计算异常 | "评分计算过程中出现异常，请检查字段数量。" | 1. 确认字段数量 2. 检查是否有重复字段 3. 重新提交 |
| E006 | 比对文件数量不足 | "比对需要至少 2 个文件，当前仅 1 个。" | 1. 补充文件内容 2. 或切换为单文件评估模式 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 常见坑 | 反模式（错误做法） | 正模式（正确做法） |
|--------|-------------------|-------------------|
| 一次提交过多文件 | 一次性粘贴 10 个文件 | 分批处理，每批不超过 5 个 |
| 忽略需核实字段 | 直接忽略 `[需核实]` 标记 | 主动补充信息或确认忽略 |
| 依赖评分做决策 | 仅凭完整度评分选择文件 | 结合使用场景和字段内容综合判断 |
| 不检查输出格式 | 直接使用未核实的对比结果 | 人工复核关键字段后再做决策 |
| 混淆能力边界 | 要求本技能评估设计逻辑质量 | 明确本技能仅评估字段完整度 |

### 6.2 反模式示例

**反模式 1：盲目信任评分**

> ❌ 错误：文件 A 评分 95%，文件 B 评分 80%，直接选 A。
>
> ✅ 正确：检查 A 的缺失字段是否影响实际使用，B 的字段是否更贴合业务场景。

**反模式 2：忽略格式匹配**

> ❌ 错误：只看字段完整度，不考虑输入输出格式是否兼容。
>
> ✅ 正确：结合集成场景，确认输入输出格式与现有系统匹配。

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```
1. 粘贴 1 个 DESIGN.md 内容 → 获取字段清单 + 评分
2. 粘贴 2-5 个 DESIGN.md 内容 → 获取对比表 + 建议
3. 遇到报错 → 查错误码表 → 按提示修正
4. 看到 [需核实] → 补充信息或确认忽略
```

### 7.2 新手路径（首次使用）

1. 阅读「一、能力边界」了解本技能能做什么、不能做什么
2. 尝试输入一个技能文件名称，观察输出格式
3. 对照「五、错误码体系」处理可能的报错
4. 逐步尝试多文件比对

### 7.3 进阶路径（熟练使用）

1. 掌握批量比对：一次提供 2-5 个文件内容
2. 自定义输出格式：指定 JSON 或特定字段排列
3. 结合置信度门控：对 `[需核实]` 字段主动补充信息
4. 利用错误码快速定位问题，减少试错

### 7.4 专家路径（深度使用）

1. 批量处理多个技能文件，输出标准化对比报告
2. 结合字段完整度评估技能文件质量
3. 基于输入输出格式匹配度给出集成建议
4. 建立技能文件选型的最佳实践流程

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应自行承担使用本 Skill 的全部责任。本 Skill 提供的评估结果、评分和建议仅供参考，不构成任何形式的保证或承诺。因使用本 Skill 而产生的任何直接或间接损失，本 Skill 作者不承担任何责任。

2. **禁止反向工程**：禁止对本 Skill 的底层逻辑、提示词结构、评分算法进行反向工程、破解、篡改或二次分发。

3. **合规使用**：使用者应确保使用本 Skill 的行为符合所在国家/地区的法律法规，不得用于任何非法用途。

4. **免责声明**：本 Skill 由 AI 辅助生成，可能存在未知缺陷或偏差。使用者应在关键决策前进行人工复核。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

### MIT License

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

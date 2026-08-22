---
slug: agent-rules-books
name: agent-rules-books
displayName: 编码规范 重构原则 领域建模速查
description: 为AI编程助手提供编码规范、重构原则与领域建模的规则速查手册。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: RuleForge Studio
agent_created: true
trigger_words: ["AGENTS.md", "rules", "skills", "coding agents", "Codex", "编码规范", "重构原则", "领域建模"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 编码规则速查手册（agent-rules-books）

## 一、能力边界速查卡

本 Skill 是面向 AI 编程助手的**规则检索与组合工具**，不替代实际编码，不生成业务代码。

| 能做 | 不能做 |
|------|--------|
| 按方法论名称检索规则条目（如 Clean Code、DDD、Refactoring） | 不提供具体代码实现方案 |
| 按主题关键词检索（如命名、聚合、重构时机） | 不评估代码质量，不执行静态分析 |
| 组合多个方法论 + 主题的交叉查询 | 不生成 AGENTS.md 配置文件本身 |
| 检测两个方法论之间的规则冲突 | 不提供团队定制化咨询服务 |
| 输出带置信度标注的规则建议 | 不保证规则适用于所有项目场景 |

**适用对象**：使用 AI 编程助手（如 Codex、Copilot 类工具）的开发者、技术负责人，以及需要将编码规范注入 AI 工作流的团队。

---

## 二、触发方式与场景映射

当输入内容包含**至少一个方法论名称**或**主题关键词**时触发。以下是大白话场景对照：

| 你说的话（输入示例） | 触发类型 | 本 Skill 做什么 |
|---------------------|---------|----------------|
| "Clean Code 命名" | 方法论 + 主题 | 返回 Clean Code 中关于命名规范的规则条目 |
| "DDD 聚合怎么设计" | 方法论 + 主题 | 返回 DDD 中聚合设计的规则条目 |
| "重构时机有哪些信号" | 主题关键词 | 返回 Refactoring 中关于重构时机的规则 |
| "组合 DDD + Refactoring" | 组合查询 | 返回两个方法论在指定主题上的交集规则 |
| "冲突 Clean Code vs DDD" | 冲突检测 | 对比两个方法论在相同主题上的规则差异 |
| "AGENTS.md 规则" | 场景词 | 返回将规则整合进 AGENTS.md 的配置建议 |

**输入格式**：不限。自然语言句子、关键词组合、命令行参数均可。

---

## 三、标准处理流程

### 前置条件

- 输入内容非空
- 输入中包含至少一个方法论名称或主题关键词

### 执行步骤

1. **格式校验**：检查输入是否为合法字符串或参数列表。格式错误返回 `E1002`。
2. **语义解析**：从输入中提取方法论名称和主题关键词。解析失败返回 `E1001`。
3. **方法论校验**：确认方法论在支持列表中。不在列表返回 `E2001`。
   - 当前支持：`Clean Code`、`DDD`（领域驱动设计）、`Refactoring`（重构）
4. **主题校验**：确认主题在支持列表中。不在列表返回 `E2002`。
   - 当前支持：`命名`、`聚合`、`重构时机`、`函数设计`、`边界上下文`、`代码坏味道`
5. **匹配执行**：
   - 单查询：直接检索方法论 + 主题的规则条目
   - 组合查询：取多个方法论在指定主题上的规则交集；无交集返回 `E3001`
   - 冲突检测：对比两个方法论在相同主题上的规则差异；无差异返回 `E3002`
6. **输出结果**：按 Markdown 规范输出，包含规则条目、示例、置信度。

### 输出规范

输出为 Markdown 格式，固定包含三个章节：

```markdown
## 规则条目
（规则编号 + 规则描述 + 来源方法论）

## 示例
（正面示例 + 反面示例）

## 置信度
（高/中/低 + 说明依据）
```

---

## 四、置信度门控

**原则：信息不足时输出占位符，绝不编造规则。**

| 置信度等级 | 判定条件 | 输出方式 |
|-----------|---------|---------|
| 高 | 规则在原始方法论中有明确原文依据 | 直接输出规则内容 |
| 中 | 规则为方法论原则的合理推论 | 输出规则 + 标注"推论" |
| 低 | 规则为跨方法论的综合建议 | 输出规则 + 标注"综合建议" |
| 需核实 | 规则涉及具体参数、阈值或版本号 | 输出 `[需核实:字段名]` 占位 |

**示例**：

> 规则 R-CC-001：命名应具有自描述性（Clean Code 第 2 章）
> 置信度：高
> 依据：方法论原文明确提及

> 规则 R-DDD-003：聚合应通过根实体访问（DDD 聚合模式推论）
> 置信度：中
> 依据：由 DDD 聚合设计原则推导

> 规则 R-RF-002：重构频率建议为每 [需核实:时间单位] 一次
> 置信度：需核实
> 说明：原始方法论未给出具体数值，需查阅具体版本

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|---------|---------|
| E1001 | 语义解析失败 | "无法从输入中识别方法论或主题关键词" | 补充方法论名称（如 Clean Code）或主题词（如命名） |
| E1002 | 格式错误 | "输入格式不正确，请使用文本或参数列表" | 检查输入是否为纯文本或合法参数 |
| E2001 | 方法论不在支持列表 | "暂不支持该方法论，当前支持：Clean Code、DDD、Refactoring" | 更换为支持列表内的方法论 |
| E2002 | 主题不在支持列表 | "暂不支持该主题，当前支持：命名、聚合、重构时机、函数设计、边界上下文、代码坏味道" | 更换为支持列表内的主题 |
| E3001 | 组合查询无交集 | "所选方法论在指定主题上没有共同规则" | 更换主题或减少方法论数量 |
| E3002 | 冲突检测无差异 | "所选方法论在指定主题上规则一致，未发现冲突" | 更换对比主题或增加方法论 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|---------|
| 过度依赖规则 | 把规则条目当作强制标准，不考虑项目上下文 | 将规则作为参考基线，结合团队实际调整 |
| 忽略置信度 | 把"低置信度"的建议当作高置信度执行 | 先核实置信度标注，再决定是否采纳 |
| 组合查询滥用 | 同时组合 3 个以上方法论，导致结果泛化 | 每次最多组合 2 个方法论，聚焦单一主题 |
| 冲突检测误读 | 把规则差异当作"谁对谁错" | 将差异视为不同场景下的权衡，而非对错 |
| 跳过格式校验 | 输入特殊字符或空内容，直接报错 | 先自查输入格式，再提交查询 |

---

## 七、渐进式阅读路径

### 速查卡（30 秒上手）

1. 输入 `方法论 + 主题` → 获取规则
2. 输入 `组合 A + B` → 获取交集
3. 输入 `冲突 A vs B` → 获取差异
4. 查看 `置信度` → 判断可信程度

### 新手路径（首次使用）

1. 阅读「一、能力边界速查卡」了解范围
2. 阅读「二、触发方式与场景映射」了解怎么用
3. 尝试简单查询：`Clean Code 命名`
4. 查看输出格式，理解置信度标注

### 进阶路径（深度使用）

1. 阅读「三、标准处理流程」理解内部逻辑
2. 尝试组合查询：`组合 DDD + Refactoring`
3. 尝试冲突检测：`冲突 Clean Code vs DDD`
4. 阅读「五、错误码体系」掌握异常处理
5. 阅读「六、FAQ 反模式对照」避免常见坑

### 专家路径（定制化）

1. 深入理解「四、置信度门控」的判定逻辑
2. 结合团队实际场景，定制规则组合
3. 将输出结果整合到 AGENTS.md 配置中
4. 定期回顾规则适用性，迭代优化

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的规则建议仅供参考，不构成任何形式的专业意见或保证。
2. **禁止反向工程**：不得对本 Skill 进行反向工程、反编译、破解或试图提取底层算法。
3. **合规使用**：使用者应确保使用方式符合所在组织及当地法律法规的要求。
4. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 许可证（License）

本 Skill 采用 MIT 许可证发布。

```
MIT License

Copyright (c) 2024 原创作者（自持版权）

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

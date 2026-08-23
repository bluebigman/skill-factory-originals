---
slug: competitor-analysis-ai
name: competitor-analysis
displayName: 竞品拆解 差异化策略 对比报告
description: 多维度拆解竞品，输出可执行差异化策略与结构化对比报告。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinAnalytics
agent_created: true
trigger_words: ["competitor-analysis", "竞品分析", "竞品对比", "竞争策略", "市场分析", "竞品拆解", "对手调研", "差异化定位"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 竞品拆解与差异化策略生成器（Competitor Analysis Skill）

## 一、能力边界：一页纸速查卡

### 1.1 本 Skill 能做什么

| 能力项 | 具体说明 | 输出物 |
|--------|----------|--------|
| 竞品信息结构化 | 将零散竞品资料整理为统一维度字段 | 竞品档案表 |
| 多维对比分析 | 支持功能、价格、体验、渠道、品牌五维对比 | 对比矩阵 |
| 差异化策略生成 | 基于对比缺口输出可执行策略建议 | 策略清单 |
| 报告结构化输出 | 生成 Markdown 格式的完整对比报告 | 报告文档 |

### 1.2 本 Skill 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不采集实时数据 | 不联网抓取竞品官网、应用商店数据，需用户自行提供素材 |
| 不做财务估值 | 不计算竞品市场份额、营收规模等财务指标 |
| 不保证策略有效性 | 策略建议基于输入信息推理，实际效果受市场环境影响 |
| 不替代人工判断 | 最终决策需结合业务实际，本 Skill 仅提供分析框架 |

### 1.3 适用对象

- 产品经理：需要快速了解竞品功能布局
- 市场运营：需要制定差异化推广策略
- 创业者：需要评估赛道竞争格局
- 分析师：需要输出结构化竞品报告

---

## 二、触发方式：场景映射表

| 用户说（大白话） | 触发词匹配 | 本 Skill 响应动作 |
|------------------|------------|-------------------|
| "帮我看看XX产品怎么样" | 竞品分析 | 启动标准分析流程 |
| "我和对手的差距在哪" | 竞品对比 | 输出多维对比矩阵 |
| "怎么打败XX" | 竞争策略 | 生成差异化策略清单 |
| "这个市场还有机会吗" | 市场分析 | 输出竞争格局评估 |
| "拆解一下XX的功能" | 竞品拆解 | 输出功能维度拆解表 |

---

## 三、标准流程：从输入到输出

### 3.1 前置条件

| 条件项 | 要求 | 缺失处理 |
|--------|------|----------|
| 目标竞品名称 | 至少 1 个 | 提示用户补充 |
| 分析维度 | 默认全维度（功能/价格/体验/渠道/品牌） | 可指定子集 |
| 参考素材 | 官网、截图、评测等任意形式 | 无素材时按通用知识分析，标注置信度 |

### 3.2 执行步骤（分步编号）

**Step 1：参数确认**
- 读取输入参数，确认竞品名称、分析维度、素材类型
- 参数缺失时，通过交互式提问补齐

**Step 2：竞品档案构建**
- 按五个维度建立竞品档案框架：
  - 功能维度：核心功能列表、特色功能、缺失功能
  - 价格维度：定价模式、价格区间、付费墙设计
  - 体验维度：交互流程、视觉风格、学习成本
  - 渠道维度：分发渠道、触达方式、合作生态
  - 品牌维度：定位语、目标人群、市场认知

**Step 3：多维对比分析**
- 将自有产品（或假设基准）与竞品逐维度对比
- 输出对比矩阵，标记差异点（优势/劣势/持平）

**Step 4：差异化策略生成**
- 基于对比缺口，生成策略建议：
  - 功能缺口 → 补足或超越策略
  - 价格缺口 → 定价调整或价值包装策略
  - 体验缺口 → 交互优化或服务升级策略
  - 渠道缺口 → 渠道拓展或合作策略
  - 品牌缺口 → 定位差异化或传播策略

**Step 5：报告输出**
- 按输出规范生成结构化报告
- 附下一步行动建议

### 3.3 输出规范

报告结构固定为以下章节：

```markdown
# 竞品分析报告：{竞品名称}
## 1. 竞品档案摘要
## 2. 多维对比矩阵
## 3. 差异化策略建议
## 4. 风险与注意事项
## 5. 下一步行动清单
```

---

## 四、置信度门控：不编造原则

### 4.1 信息不足时的处理

当输入素材不足以支撑分析时，使用以下占位符：

| 场景 | 占位符 | 示例 |
|------|--------|------|
| 竞品价格未知 | `[需核实:价格]` | 定价策略：`[需核实:价格]` |
| 竞品功能不明确 | `[需核实:功能列表]` | 核心功能：`[需核实:功能列表]` |
| 市场份额无数据 | `[需核实:市场份额]` | 市场地位：`[需核实:市场份额]` |
| 用户评价缺失 | `[需核实:用户反馈]` | 体验评价：`[需核实:用户反馈]` |

### 4.2 置信度标注规则

- 基于用户提供素材的分析：标注 `[置信度:高]`
- 基于通用行业知识的推断：标注 `[置信度:中]`
- 基于假设的推测：标注 `[置信度:低]` 并附假设前提

---

## 五、错误码体系

| 错误码 | 错误场景 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 未提供竞品名称 | "请提供至少一个竞品名称，例如：'分析一下XX产品'" | 补充竞品名称后重试 |
| E002 | 分析维度无效 | "支持的维度为：功能、价格、体验、渠道、品牌" | 重新指定维度子集 |
| E003 | 素材格式不识别 | "无法解析该素材格式，支持文本、表格、链接描述" | 转换为文本描述后重试 |
| E004 | 对比基准缺失 | "请说明对比基准，例如：'以我们的产品XX为基准'" | 指定基准产品或使用通用基准 |
| E005 | 策略生成失败 | "差异化策略生成失败，请检查输入参数是否完整" | 确认竞品档案完整性后重试 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正确姿势 |
|--------|-------------------|----------|
| 信息过载 | 一次性输入 20 个竞品，要求全维度分析 | 每次聚焦 1-3 个竞品，分批分析 |
| 数据幻觉 | 要求"估算竞品营收" | 明确标注 `[需核实:营收]`，不推测财务数据 |
| 策略空泛 | 期望输出"打败对手"的万能方案 | 基于具体差异点生成可执行策略 |
| 忽略边界 | 要求分析未提供的内部数据 | 明确告知数据边界，建议补充素材 |
| 绝对化表述 | 使用"这个策略一定有效" | 策略建议附带前提条件和风险提示 |

---

## 七、渐进式披露：分层次阅读路径

### 7.1 速查卡（30 秒上手）

```
输入：竞品名称 + 可选维度
流程：确认参数 → 构建档案 → 对比分析 → 生成策略 → 输出报告
输出：五维对比矩阵 + 差异化策略清单
注意：信息不足时使用 [需核实:字段] 占位
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」了解适用范围
2. 参考「触发方式」准备输入格式
3. 按「标准流程」执行一次完整分析
4. 遇到问题查阅「错误码体系」

### 7.3 进阶路径（熟练使用）

1. 自定义分析维度组合（如仅分析"功能+价格"）
2. 批量分析多个竞品并交叉对比
3. 结合「置信度门控」评估分析可靠性
4. 将策略建议转化为行动清单并跟踪执行

---

## 八、参数配置参考

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| competitor_name | string | 是 | 无 | 竞品名称，支持多个用逗号分隔 |
| dimensions | array | 否 | ["功能","价格","体验","渠道","品牌"] | 分析维度子集 |
| baseline | string | 否 | "通用基准" | 对比基准，可为自有产品或行业标准 |
| material_type | string | 否 | "text" | 素材类型：text/table/link |
| output_format | string | 否 | "markdown" | 输出格式，当前仅支持 markdown |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者应自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的分析结果和建议仅供参考，不构成任何形式的决策依据。因使用本 Skill 输出内容而导致的任何直接或间接损失，Skill 作者及贡献者不承担任何责任。

2. **禁止反向工程**：使用者不得对本 Skill 的提示词结构、处理逻辑、内部机制进行反向工程、破解、提取或二次分发。本 Skill 的完整提示词受版权保护。

3. **内容使用**：本 Skill 生成的输出内容可用于商业或非商业用途，但不得移除输出中的置信度标注和需核实占位符。

4. **合规使用**：使用者应确保输入素材的合法性和合规性，不得使用本 Skill 进行任何违反法律法规的活动。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 LinAnalytics

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

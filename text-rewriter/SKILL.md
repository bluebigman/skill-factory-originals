---
slug: text-rewriter
name: text-rewriter
displayName: 文本自然化 去AI腔调 润色改写
description: 去除AI腔调，让文字更自然，适合润色改写各类文本。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林默
agent_created: true
trigger_words: ["去AI味", "润色改写", "text rewriter", "文本去机械化", "自然化改写", "消除机器感", "人性化表达"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 文本自然化 · 去AI腔调改写 Skill

本 Skill 由 AI 辅助生成，仅供参考。它提供一套系统化的方法，帮助你将带有明显机器生成痕迹的文本，改写为更接近人类自然书写习惯的表达。

---

## 一、能力边界（一页纸速查卡）

### 能做什么

| 能力项 | 说明 | 示例场景 |
|--------|------|----------|
| 去除机械句式 | 消除"首先/其次/最后""总而言之"等模板化连接词 | 报告、总结、说明文 |
| 软化生硬措辞 | 将"值得注意的是""不难发现"等AI高频套话替换为自然表达 | 文章、邮件、自媒体 |
| 调整语序节奏 | 打破主谓宾过于规整的句式，增加长短句交错 | 散文、评论、叙事 |
| 保留原意改写 | 在不改变事实信息的前提下重写表达方式 | 新闻稿、产品介绍 |
| 批量文本处理 | 对多段落、多文件进行统一风格的改写 | 文档集、网站文案 |

### 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不改变事实数据 | 数字、日期、专有名词、引用内容保持原样 |
| 不做内容扩写 | 不添加原文没有的信息、案例或观点 |
| 不做风格迁移 | 不将严肃文风改为幽默文风，除非用户明确要求 |
| 不处理非文本格式 | 表格、代码、公式等结构化内容不在改写范围内 |
| 不保证文学水准 | 目标是"自然"，不是"优美"，不承诺达到文学创作水平 |

### 适用对象

- 需要将AI生成内容转为更自然表达的写作者
- 需要批量处理文案的运营人员
- 对文本"机器感"敏感、追求自然阅读体验的普通用户

---

## 二、触发方式

### 触发词

直接使用以下任一说法即可唤起本 Skill：

- "去AI味"
- "润色改写"
- "text rewriter"
- "文本去机械化"
- "自然化改写"
- "消除机器感"
- "人性化表达"

### 场景映射表

| 你说的话（大白话） | Skill 实际做的事 |
|-------------------|------------------|
| "这段话一看就是AI写的，帮我改改" | 识别机械句式与套话，替换为自然表达 |
| "帮我润色一下这段文字" | 在保留原意基础上优化措辞与节奏 |
| "这文章读起来太生硬了" | 调整句式结构，增加语言流畅度 |
| "把这段改得像人写的" | 去除AI高频用词与模板化结构 |

---

## 三、标准流程

### 前置条件

1. 待处理文本以 `.txt` 或 `.md` 格式保存，编码为 UTF-8
2. 文件命名建议：`input_01.txt`、`input_02.txt` 等，便于批量处理
3. 确认原始文本中不包含需要保留的特殊格式（如加粗、斜体标记）

### 执行步骤

**第一步：单样本试运行**

选取一个代表性段落（建议 200-500 字），执行改写：

```
输入：原始段落
输出：改写后段落 + 修改说明（列出主要改动点）
```

核对以下字段：
- 事实信息是否完整保留（数字、名称、日期）
- 改写后是否仍有明显AI痕迹
- 语气是否自然流畅

**第二步：批量执行**

确认单样本效果满意后，对全部文件执行改写。每个文件输出格式：

```
文件名 | 原字数 | 改写字数 | 主要改动类型
```

**第三步：结果校验**

随机抽取 20% 输出条目，逐项核对：
- 关键信息（人名、地名、数字）与源文件一致
- 无新增事实性错误
- 无遗漏段落

### 输出规范

| 输出项 | 格式要求 |
|--------|----------|
| 改写文本 | 纯文本，保留原始段落结构 |
| 修改说明 | 每条不超过 50 字，列出 2-3 个主要改动点 |
| 校验报告 | 包含抽查比例、通过率、问题清单 |

---

## 四、置信度门控

当遇到以下情况时，**不猜测、不编造**，输出 `[需核实:字段名]` 占位符：

| 情况 | 处理方式 |
|------|----------|
| 原文存在明显笔误或矛盾信息 | 保留原文，标注 `[需核实:此处信息矛盾]` |
| 涉及专业术语或行业黑话 | 不擅自替换，标注 `[需核实:术语准确性]` |
| 引用的数据或来源不明确 | 保留原表述，标注 `[需核实:数据来源]` |
| 改写后可能产生歧义 | 在修改说明中特别提示 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| ERR_EMPTY_INPUT | 输入为空 | "未检测到可处理的文本内容" | 检查文件是否为空或格式是否正确 |
| ERR_ENCODING | 编码不支持 | "文件编码不是 UTF-8，请转换后重试" | 用文本编辑器另存为 UTF-8 格式 |
| ERR_TOO_SHORT | 文本过短 | "文本少于 50 字，改写空间有限" | 确认是否确实需要改写，或补充上下文 |
| ERR_NO_CHANGE | 未检测到AI痕迹 | "该文本已接近自然表达，无需大幅改动" | 可微调个别措辞，或直接保留原文 |
| ERR_BATCH_ABORT | 批量处理中断 | "批量处理在第 N 个文件中断，请检查该文件" | 定位问题文件，单独处理后重新执行 |

---

## 六、FAQ 反模式

### 常见坑与正确做法

| 常见错误做法 | 问题所在 | 正确做法 |
|-------------|----------|----------|
| 把所有短句合并成长句 | 过度改写，失去原文节奏 | 保持长短句交错，保留原文语气 |
| 替换所有"的"为"之" | 矫枉过正，反而显得做作 | 只替换明显生硬的表达 |
| 删除所有连接词 | 逻辑关系变得模糊 | 保留必要的逻辑连接，只去掉模板化套话 |
| 追求每句都"有文采" | 过度修饰，偏离自然目标 | 目标是自然流畅，不是华丽辞藻 |
| 忽略原文语气和立场 | 改写后语气与原文不符 | 先判断原文基调（正式/轻松/严肃），保持一致 |

### 反模式对照表

| 反模式 | 示例 | 正确改写 |
|--------|------|----------|
| 模板化开头 | "首先，我们需要认识到..." | "先得搞清楚一件事..." |
| 空洞强调 | "值得注意的是，这个问题很重要" | "这个问题确实不能忽视" |
| 机械总结 | "综上所述，我们可以得出结论" | "说到底，情况就是这样" |
| 生硬转折 | "然而，我们必须看到另一方面" | "不过，事情还有另一面" |

---

## 七、渐进式披露

### 速查卡（30秒上手）

1. 准备文本文件（UTF-8 编码）
2. 先拿一段试改写，确认效果
3. 批量处理，保留原始文件备份
4. 抽查校验，确认信息无误

### 新手路径（首次使用）

- 阅读"能力边界"了解适用范围
- 用一段 200 字左右的文本试运行
- 对照"输出规范"检查结果
- 遇到问题查"错误码体系"

### 进阶路径（熟练使用）

- 自定义改写风格偏好（如更口语化/更书面化）
- 对批量处理结果做统计分析，优化改写策略
- 结合"置信度门控"处理复杂文本中的模糊信息
- 建立个人常用表达库，提高改写一致性

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。包括但不限于因改写结果引发的任何直接或间接损失。
2. **禁止反向工程**：不得对本 Skill 的提示词结构、生成逻辑进行反向工程、破解或提取核心算法。
3. **合规使用**：不得使用本 Skill 生成违反法律法规、社会公序良俗的内容。
4. **内容审核**：使用者应对最终输出内容自行审核，确保其准确性、合法性和适当性。

<!-- user-agreement-injected -->

---

## 许可证（License）

本 Skill 采用 MIT 许可证发布。

### MIT License

```
MIT License

Copyright (c) 2024 林默

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

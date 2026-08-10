---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: deeppapernote
name: deeppapernote
displayName: 论文精读 Obsidian 结构化笔记
description: 深度阅读单篇论文，自动生成结构化 Obsidian 风格研究笔记。
version: 2.0.1
rules_version: cpr-20260810-n301
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/deeppapernote
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 知微研墨
agent_created: true
trigger_words: ["论文精读", "研究笔记", "Obsidian笔记", "文献阅读", "论文拆解", "学术笔记"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 论文精读 Obsidian 结构化笔记（deeppapernote）

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 能力项 | 说明 | 输出形态 |
|--------|------|----------|
| 单篇论文深度解析 | 输入 PDF 文本或论文 URL，提取核心内容 | 结构化 Markdown 笔记 |
| Obsidian 语法适配 | 自动生成 Wiki 链接、标签、Callout、双链 | `.md` 文件，可直接放入 Obsidian Vault |
| 研究脉络梳理 | 提取研究背景、问题、方法、实验、结论 | 分节笔记，含逻辑关联 |
| 概念与术语抽取 | 识别论文中的关键概念、方法名、指标 | 术语表 + 定义 |
| 引用与延伸阅读 | 提取参考文献中的关键条目 | 延伸阅读清单 |
| 个人批注预留 | 生成可编辑的思考区、疑问区 | 占位符 + 引导问题 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不处理多篇论文 | 一次只处理一篇，批量任务需多次调用 |
| 不生成全文翻译 | 仅做结构化摘要，不做逐句翻译 |
| 不替代原文阅读 | 笔记是辅助，核心结论需对照原文核实 |
| 不保证数据准确性 | 实验数据、引用信息以原文为准，AI 提取可能有误 |
| 不处理扫描版 PDF | 需先经 OCR 转换为可复制文本 |

### 1.3 适用对象

- 研究生、科研人员：需要快速掌握一篇论文的框架与贡献
- Obsidian 用户：希望将文献笔记纳入个人知识库
- 学术写作者：需要整理文献综述素材
- 深度学习者：想系统拆解一篇复杂论文

---

## 二、触发方式：场景映射表

### 2.1 触发词

- 主触发词：`论文精读`、`研究笔记`、`Obsidian笔记`
- 补充触发词：`文献阅读`、`论文拆解`、`学术笔记`

### 2.2 场景映射

| 用户说（大白话） | 实际意图 | 触发动作 |
|------------------|----------|----------|
| "帮我读一下这篇论文，整理成笔记" | 需要结构化摘要 | 执行标准流程，生成完整笔记 |
| "这篇论文讲了什么？" | 快速了解核心内容 | 生成精简版笔记（仅摘要+结论） |
| "把这篇论文放进我的 Obsidian" | 需要可直接导入的 Markdown | 生成带 YAML frontmatter 和 Wiki 链接的完整笔记 |
| "这篇论文的方法部分帮我拆解一下" | 深入分析方法论 | 生成方法专章笔记 |
| "这篇论文和另一篇有什么关系？" | 需要关联分析 | 生成笔记时附加关联建议（需用户提供另一篇信息） |

---

## 三、标准流程：从输入到输出

### 3.1 前置条件

| 条件 | 要求 | 缺失处理 |
|------|------|----------|
| 论文文本 | 可复制的文本格式（TXT/MD/HTML/可复制 PDF） | 提示用户先进行 OCR 或手动复制 |
| 论文元信息 | 标题、作者、年份、期刊/会议（至少标题） | 从文本中自动提取，提取失败则标注 [需核实:字段] |
| 输出目录 | 用户指定或默认当前目录 | 默认生成在 `./notes/` 下 |

### 3.2 执行步骤

**Step 1：输入接收**
- 接收论文文本（直接粘贴或提供文件路径）
- 接收可选参数：论文标题、作者、年份、期刊、DOI、标签

**Step 2：元信息提取**
- 从文本开头提取标题、作者、单位、摘要
- 提取失败时使用 `[需核实:标题]` 等占位符

**Step 3：结构解析**
- 识别论文的章节结构（Introduction / Methods / Results / Discussion / Conclusion）
- 提取每个章节的核心内容，压缩为要点

**Step 4：深度内容抽取**

| 抽取项 | 说明 | 输出格式 |
|--------|------|----------|
| 研究问题 | 论文要解决的核心问题 | `> [!question] 研究问题` |
| 核心方法 | 提出的方法/模型/框架 | `> [!info] 核心方法` |
| 关键实验 | 实验设置、数据集、基线 | `> [!example] 实验设计` |
| 主要结果 | 关键数据、对比结果 | `> [!success] 主要结果` |
| 结论与贡献 | 论文的结论和贡献点 | `> [!summary] 结论与贡献` |

**Step 5：概念与术语抽取**
- 提取论文中的专业术语、方法名、指标名
- 生成术语表，每个术语附简短定义

**Step 6：引用与延伸阅读**
- 提取参考文献中的关键条目（标题、作者、年份）
- 标注与本文的关联度（高/中/低）

**Step 7：笔记组装**
- 按 Obsidian 语法组装为完整 Markdown 文件
- 添加 YAML frontmatter、标签、Wiki 链接、Callout

**Step 8：输出与确认**
- 输出笔记文件路径
- 提供简要的笔记结构预览
- 提示用户检查 [需核实] 字段

### 3.3 输出规范

**文件命名**：`论文笔记-{第一作者}-{年份}-{标题前6字}.md`

**YAML frontmatter 模板**：
```yaml
---
title: "论文标题"
authors: ["作者1", "作者2"]
year: 2024
venue: "期刊/会议名"
doi: "DOI号"
tags: ["文献笔记", "研究方向"]
type: paper-note
source: "原文链接或来源"
created: 2026-08-10
---
```

**正文结构模板**：
```markdown
# 论文标题

> [!abstract] 摘要
> 论文摘要内容

## 研究背景与动机
- 背景要点1
- 背景要点2

## 研究问题
> [!question] 核心问题
> 问题描述

## 核心方法
> [!info] 方法概述
> 方法描述

### 方法细节
- 步骤1
- 步骤2

## 实验与结果
> [!example] 实验设置
> 数据集、基线、评估指标

> [!success] 关键结果
> 结果数据

## 结论与贡献
- 贡献点1
- 贡献点2

## 局限与展望
- 局限1
- 展望1

## 术语表
| 术语 | 定义 |
|------|------|
| 术语1 | 定义1 |

## 延伸阅读
- [ ] 参考文献1（关联度：高）
- [ ] 参考文献2（关联度：中）

## 个人批注
> [!note] 思考
> 这里写你的想法

> [!warning] 疑问
> 这里写你的疑问
```

---

## 四、置信度门控

### 4.1 占位符规则

当信息不足或提取不确定时，使用以下占位符，**绝不编造**：

| 占位符 | 使用场景 |
|--------|----------|
| `[需核实:标题]` | 无法确定论文标题时 |
| `[需核实:作者]` | 作者信息缺失或不确定时 |
| `[需核实:年份]` | 年份无法确认时 |
| `[需核实:数据]` | 实验数据提取不确定时 |
| `[需核实:引用]` | 参考文献信息不完整时 |
| `[需核实:术语定义]` | 术语定义无法准确提取时 |

### 4.2 置信度标注

- 高置信度（>90%）：直接从原文明确提取，不加标注
- 中置信度（70-90%）：在内容后加 `（提取自原文，建议核实）`
- 低置信度（<70%）：使用 `[需核实:字段]` 占位

### 4.3 禁止行为

- 禁止推测作者意图
- 禁止补充原文未提及的数据
- 禁止将摘要内容当作全文结论

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| ERR-001 | 输入文本为空 | "未检测到论文文本，请提供论文内容" | 1. 确认文本已复制 2. 检查文件路径 3. 重新输入 |
| ERR-002 | 文本过短（<500字符） | "输入文本过短，可能不是完整论文" | 1. 检查是否只复制了摘要 2. 补充完整文本 3. 重新执行 |
| ERR-003 | 无法识别章节结构 | "未能识别论文的标准章节结构" | 1. 确认文本包含完整论文 2. 尝试手动指定章节 3. 使用宽松模式 |
| ERR-004 | 元信息提取失败 | "无法提取论文标题/作者/年份" | 1. 手动提供元信息 2. 使用占位符继续 3. 检查文本开头格式 |
| ERR-005 | 输出目录不可写 | "无法写入输出目录" | 1. 检查目录权限 2. 更换输出目录 3. 使用默认目录 |
| ERR-006 | 术语提取异常 | "术语提取过程中出现异常" | 1. 简化文本输入 2. 分段处理 3. 手动补充术语表 |

---

## 六、FAQ 反模式对照

### 反模式 1：过度依赖 AI 摘要

**错误做法**：直接引用 AI 生成的摘要作为论文结论，不阅读原文。

**正确做法**：将 AI 笔记作为导航地图，关键结论必须回到原文验证。

### 反模式 2：忽略置信度标注

**错误做法**：将 `[需核实]` 字段当作确定信息直接使用。

**正确做法**：遇到占位符立即核实，补充正确信息后再使用笔记。

### 反模式 3：笔记堆积不整理

**错误做法**：生成大量笔记但从不回看、不建立关联。

**正确做法**：每次生成后花 5 分钟添加个人批注，建立与其他笔记的双链。

### 反模式 4：输入不完整文本

**错误做法**：只粘贴摘要或部分章节，期望得到完整分析。

**正确做法**：提供完整论文文本，至少包含摘要+引言+结论。

### 反模式 5：期望 AI 理解图表

**错误做法**：认为 AI 能解析论文中的图表数据。

**正确做法**：图表数据需人工阅读，AI 仅处理文本信息。

---

## 七、渐进式披露：分层次阅读路径

### 7.1 速查卡（30 秒版）

```
论文精读 → 输入文本 → 自动生成 Obsidian 笔记
├── 输入：论文全文文本
├── 输出：结构化 Markdown 文件
├── 包含：摘要、方法、实验、结论、术语表
├── 特点：Obsidian 语法、双链、Callout
└── 注意：[需核实] 字段需人工确认
```

### 7.2 新手路径（5 分钟上手）

1. 复制论文全文文本
2. 输入 `论文精读` + 粘贴文本
3. 等待生成，检查输出文件
4. 将文件放入 Obsidian Vault
5. 阅读笔记，对照原文核实关键信息

### 7.3 进阶路径（深度使用）

1. **自定义标签体系**：在输入时指定 `tags: ["深度学习", "Transformer"]` 等自定义标签
2. **关联笔记**：生成后手动添加 `[[相关论文]]` 双链
3. **批注深化**：在个人批注区记录思考、疑问、延伸想法
4. **模板定制**：根据个人偏好调整输出模板（需修改 Skill 配置）
5. **批量处理**：多次调用，每次处理一篇，统一放入同一 Vault 目录

### 7.4 参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `text` | string | 必填 | 论文全文文本 |
| `title` | string | 自动提取 | 论文标题 |
| `authors` | string[] | 自动提取 | 作者列表 |
| `year` | number | 自动提取 | 发表年份 |
| `venue` | string | 自动提取 | 期刊/会议 |
| `tags` | string[] | `["文献笔记"]` | 自定义标签 |
| `output_dir` | string | `./notes/` | 输出目录 |
| `detail_level` | string | `full` | 详细程度：`full`/`brief` |

---

## 八、使用示例

### 示例 1：标准精读

**输入**：
```
论文精读
标题：Attention Is All You Need
作者：Vaswani et al.
年份：2017
标签：["NLP", "Transformer"]
[粘贴论文全文]
```

**输出**：`论文笔记-Vaswani-2017-Attention.md`

### 示例 2：快速摘要

**输入**：
```
论文精读，只要摘要和结论
[粘贴论文全文]
```

**输出**：精简版笔记，仅包含摘要、核心方法概述、结论。

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担全部责任。本 Skill 生成的笔记内容仅供参考，不构成学术建议或研究结论。因使用本 Skill 产生的任何直接或间接损失，Skill 作者及 AI 辅助生成方不承担任何责任。

2. **内容核实**：使用者有义务对生成内容进行核实，特别是涉及数据、引用、结论的部分。AI 生成内容可能存在错误或偏差。

3. **禁止反向工程**：禁止对本 Skill 进行反向工程、破解、篡改或试图提取底层算法。

4. **合规使用**：使用者应遵守所在机构、期刊、出版社关于文献使用的相关规定，尊重原作者版权。

5. **免责声明**：本 Skill 为 AI 辅助生成工具，不保证输出内容的完整性、准确性和适用性。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 知微研墨

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

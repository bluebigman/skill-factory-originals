---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: humanizer-czech
name: humanizer-czech
displayName: 捷克语文本 自然化改写 去机翻味
description: 将机器生成文本改写为自然人类表达，适配捷克语语境。
version: 1.0.2
rules_version: cpr-20260817-n526
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/humanizer-czech
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaCraft Studio
agent_created: true
trigger_words: ["去AI味", "润色改写", "humanizer czech", "自然化处理", "文本人性化", "捷克语润色", "消除机翻感"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# SKILL.md — humanizer-czech

## 一、能力边界：一页纸速查卡

本 Skill 专注解决一个核心问题：**将捷克语环境中带有明显机器生成痕迹的文本，改写为符合人类自然表达习惯的版本**。它面向的是文本风格转换，而非翻译或内容创作。

### 1.1 能做什么

| 能力项 | 说明 | 示例场景 |
|--------|------|----------|
| 去模板化 | 消除重复句式、僵硬连接词 | 将 "V souladu s výše uvedeným..." 改为自然过渡 |
| 语气自然化 | 调整过于正式或生硬的措辞 | 将被动结构改为主动表达 |
| 语境适配 | 根据文本类型调整正式度 | 商务邮件 vs 社交媒体帖子 |
| 冗余压缩 | 删减机器生成常见的重复信息 | 合并同义反复的句子 |
| 文化校准 | 修正不符合捷克语习惯的表达 | 调整数字格式、日期表达、称呼方式 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不做翻译 | 输入必须是捷克语文本，不提供从其他语言翻译为捷克语的功能 |
| 不改变事实 | 只调整表达方式，不修改原文中的事实性信息、数据、专有名词 |
| 不生成新内容 | 不添加原文没有的观点、建议或结论 |
| 不处理超长文本 | 单次处理上限为 5000 字符（约 800 词），超出需分段 |
| 不保证文学性 | 目标是自然流畅，不追求文学修辞效果 |

### 1.3 适用对象

- **内容运营人员**：需要将产品描述、公告等批量文本人性化
- **本地化工程师**：处理机器翻译后的捷克语文本润色
- **跨境电商从业者**：优化面向捷克市场的商品文案
- **学术研究人员**：整理非正式场合的捷克语交流记录

---

## 二、触发方式：场景映射表

当你的需求与下表左侧场景匹配时，可直接使用对应的触发词启动本 Skill。

| 场景描述（大白话） | 触发词 | 预期输出 |
|-------------------|--------|----------|
| "这段捷克语读起来像机器人写的，帮我改得像人话" | 去AI味 | 自然化改写后的文本 |
| "把这份产品说明润色一下，别那么生硬" | 润色改写 | 流畅度提升的文本 |
| "需要把机翻的捷克语调整得更地道" | humanizer czech | 符合捷克语习惯的文本 |
| "让这段文字不那么机械，更像真人写的" | 自然化处理 | 去机械化表达的文本 |
| "整体优化一下，让语气更自然" | 文本人性化 | 人性化调整后的文本 |
| "捷克语文案读着别扭，帮忙顺一顺" | 捷克语润色 | 通顺自然的捷克语文本 |
| "这明显是翻译软件生成的，改一下" | 消除机翻感 | 消除翻译痕迹的文本 |

**使用提示**：触发词可以组合使用，例如"去AI味 + 捷克语润色"表示优先处理机械感问题，同时兼顾语言地道性。

---

## 三、标准流程：从输入到输出

### 3.1 前置条件

| 条件项 | 要求 | 检查方法 |
|--------|------|----------|
| 输入格式 | 纯文本或 UTF-8 编码的 .txt/.md 文件 | 打开文件确认无乱码 |
| 语言确认 | 文本主体为捷克语（允许少量英语术语） | 抽查 3-5 个句子确认 |
| 文本长度 | 单次不超过 5000 字符 | 使用 `wc -c` 或编辑器字数统计 |
| 内容类型 | 非诗歌、非法律合同、非医学处方 | 目测判断文本类型 |

### 3.2 执行步骤

**步骤 1：输入准备**

将待处理文本保存为 `.txt` 文件，命名格式建议：`input_[描述性名称].txt`。例如：`input_produkt_popis.txt`。

**步骤 2：单样本试运行**

选取文本中 200-300 字符的片段进行试处理：

```
输入示例（原文）：
"Tento produkt je navržen tak, aby poskytoval uživatelům maximální komfort během používání. Produkt je vyroben z vysoce kvalitních materiálů, které zajišťují dlouhou životnost produktu."

输出示例（改写后）：
"Tento produkt vás při každém použití přesvědčí svým pohodlím. Díky kvalitním materiálům vám bude sloužit dlouhá léta."
```

**步骤 3：核对输出字段**

检查输出是否满足以下规范：

| 检查项 | 标准 | 通过标准 |
|--------|------|----------|
| 事实保留 | 所有数据、日期、专有名词与原文一致 | 逐项比对 |
| 语气变化 | 从机械/正式变为自然/流畅 | 通读感受 |
| 长度控制 | 改写后长度在原文的 70%-130% 之间 | 字符数对比 |
| 语言正确 | 无语法错误、无语义歧义 | 捷克语母语者或高级工具验证 |

**步骤 4：批量执行**

确认单样本输出合格后，对全量文本执行处理。处理过程中保留原始文件备份，命名格式：`backup_[原始文件名]_[时间戳].txt`。

**步骤 5：结果校验**

随机抽取 20% 的输出条目，核对以下关键点：

- 关键数据（价格、日期、型号）是否与源文件一致
- 是否存在过度改写导致的信息丢失
- 是否有未处理的机器痕迹（如重复的句式结构）

### 3.3 输出规范

| 输出项 | 格式要求 |
|--------|----------|
| 主输出 | 纯文本，UTF-8 编码，无额外标记 |
| 处理报告 | 包含：处理条目数、平均改写率、异常条目数 |
| 备份文件 | 原始输入文件的完整副本 |

---

## 四、置信度门控：不编造原则

当遇到以下情况时，输出中必须使用 `[需核实:字段名]` 占位符，而非猜测或编造：

| 场景 | 处理方式 | 示例 |
|------|----------|------|
| 原文存在模糊信息 | 保留原文表述，标记需核实 | "termín dodání je [需核实:交付日期]" |
| 专有名词不确定 | 保留原文拼写，标记需核实 | "společnost [需核实:公司名称] oznámila..." |
| 数据格式不明确 | 保留原格式，标记需核实 | "cena je [需核实:价格单位]" |
| 文化引用不确定 | 不强行解释，标记需核实 | "odkaz na [需核实:文化引用]" |

**门控规则**：

1. 当原文信息不足以支撑自然改写时，优先保留原句结构，仅做最小调整
2. 当改写可能引入歧义时，在输出末尾添加注释说明
3. 当文本类型超出能力边界时，直接输出原文并附说明

---

## 五、错误码体系：问题诊断与修正

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 输入文本非捷克语 | "检测到输入文本主体非捷克语，请确认语言。" | 检查输入文件编码和语言，更换为捷克语文本 |
| E002 | 文本长度超限 | "输入文本超过 5000 字符限制，请分段处理。" | 将文本按段落或逻辑单元拆分为多个文件 |
| E003 | 事实性信息冲突 | "改写后数据与原文不一致，请检查。" | 对比原文与输出，修正被改动的数据 |
| E004 | 过度改写 | "输出文本与原文语义偏差过大，请调整改写强度。" | 减少改写幅度，保留更多原文句式 |
| E005 | 无法识别文本类型 | "无法确定文本类型，请指定文本用途。" | 在输入文件头部添加注释说明文本类型 |
| E006 | 输出为空 | "处理失败，未生成输出。" | 检查输入文件是否为空，重新执行 |

---

## 六、FAQ 反模式：常见坑与对照

### 坑 1：过度追求"自然"而丢失专业性

**反模式**：将技术文档改写为过于口语化的表达，导致专业术语丢失。

**正确做法**：保持专业术语不变，仅调整连接词和句式结构。例如：

```
原文：Zařízení je nutné kalibrovat každých 6 měsíců.
反模式（错误）：Tu věc musíš každou chvíli seřizovat.
正确（推荐）：Zařízení vyžaduje kalibraci každých 6 měsíců.
```

### 坑 2：忽略捷克语的大小写规则

**反模式**：改写时随意改变专有名词的大小写。

**正确做法**：捷克语中，专有名词、品牌名、地名等保持原大小写。例如：

```
原文：Společnost Apple představila nový iPhone.
反模式（错误）：společnost apple představila nový iphone.
正确（推荐）：Apple představila nový iPhone.
```

### 坑 3：将所有被动句改为主动句

**反模式**：机械地将所有被动结构改为主动，导致语义变化。

**正确做法**：根据语境判断。捷克语中被动结构在某些场景（如官方文件）是标准用法。

```
原文：Rozhodnutí bylo učiněno vedením společnosti.
反模式（错误）：Vedení společnosti učinilo rozhodnutí. （改变了强调重点）
正确（推荐）：Vedení společnosti rozhodnutí učinilo. （保留被动含义，调整语序）
```

### 坑 4：忽略文本的受众差异

**反模式**：对面向儿童和面向律师的文本使用相同的改写策略。

**正确做法**：根据受众调整改写程度。面向专业受众时保留术语和正式结构；面向大众时增加解释性内容。

### 坑 5：批量处理时未保留原始数据

**反模式**：直接覆盖原文件，导致无法回溯。

**正确做法**：始终保留备份文件，并在处理报告中记录每次改动的版本信息。

---

## 七、渐进式披露：分层次阅读路径

### 速查卡（30 秒上手）

```
1. 输入：捷克语文本（≤5000字符）
2. 触发：说"去AI味"或"humanizer czech"
3. 输出：自然化改写文本 + 处理报告
4. 校验：抽查 20% 输出，核对数据一致性
5. 备份：原始文件保留，命名加时间戳
```

### 新手路径（首次使用）

1. 阅读「能力边界」了解适用范围
2. 使用「触发方式」中的场景映射找到合适的启动方式
3. 按照「标准流程」的步骤 1-3 完成一次单样本测试
4. 确认输出合格后，再进行批量处理

### 进阶路径（熟练用户）

1. 深入理解「置信度门控」机制，处理模糊信息
2. 熟悉「错误码体系」，快速定位和解决问题
3. 参考「FAQ 反模式」避免常见错误
4. 根据文本类型自定义改写策略（如商务 vs 技术文档）

---

## 八、技术参数与配置

| 参数名 | 默认值 | 可调范围 | 说明 |
|--------|--------|----------|------|
| 改写强度 | 中等 | 保守/中等/激进 | 保守：仅调整连接词；激进：重构句式 |
| 术语保留 | 开启 | 开启/关闭 | 关闭时允许将专业术语替换为通俗表达 |
| 长度控制 | 100% | 70%-130% | 输出长度与原文的比例 |
| 语气目标 | 自然 | 正式/自然/亲切 | 根据文本类型自动选择或手动指定 |

---

## 九、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。包括但不限于因改写结果引发的任何直接或间接损失。
2. **禁止反向工程**：不得对本 Skill 的提示词结构、处理逻辑进行反向工程、破解或提取核心算法。
3. **合规使用**：不得将本 Skill 用于生成违法、侵权、欺诈性内容。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

本 Skill 采用 MIT 许可证授权：

```
MIT License

Copyright (c) 2026 LinguaCraft Studio

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

## 附录：处理报告模板

```markdown
# 处理报告

- 处理时间：[日期时间]
- 输入文件：[文件名]
- 输出文件：[文件名]
- 处理条目数：[数量]
- 平均改写率：[百分比]
- 异常条目：[数量及错误码]
- 备份文件：[备份文件名]

## 异常详情

| 条目 | 错误码 | 处理方式 |
|------|--------|----------|
| [条目标识] | [错误码] | [处理说明] |
```

---

*文档版本：1.0.0 | 最后更新：2026-08-17*

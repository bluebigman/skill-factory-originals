---
slug: humanizer-czech
name: humanizer-czech
displayName: 捷克语文本 自然化改写 去机翻味
description: 将机器生成文本改写为自然人类表达，适配捷克语语境。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: lingo-craft-studio
agent_created: true
trigger_words: ["去AI味", "润色改写", "humanizer czech", "自然化处理", "文本人性化", "捷克语润色", "消除机翻痕迹"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

# 捷克语文本自然化改写 Skill（humanizer-czech）

## 一、能力边界速查卡

### 1.1 能做什么

| 能力项 | 说明 | 示例场景 |
|--------|------|----------|
| 机器文本自然化 | 将翻译引擎、LLM 生成的捷克语文本改写为母语者表达 | 产品说明、客服回复、邮件正文 |
| 语序调整 | 优化捷克语语序（捷克语为自由语序语言，但存在信息结构惯例） | 将被动结构转为主动，调整主题-述题排列 |
| 词汇替换 | 替换生硬直译词、过度正式词，选用语境贴切的近义词 | "provést implementaci" → "zavést" |
| 语气调节 | 根据目标读者调整正式度（正式/中性/口语） | 面向普通用户的帮助文档去掉官僚腔 |
| 格式适配 | 处理捷克语标点、引号（„ “）、数字格式（空格千分位） | 将英文引号转为捷克语引号 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不处理非捷克语文本 | 输入需为捷克语或明显可判定的捷克语混合文本 |
| 不进行事实核查 | 不验证原文中的日期、数字、专有名词的真实性 |
| 不翻译 | 本 Skill 不做跨语言翻译，仅做捷克语内部的自然化改写 |
| 不生成新内容 | 不添加原文没有的信息，仅优化表达方式 |
| 不保证文学级质量 | 目标为"自然、可读、无机器痕迹"，非文学创作 |

### 1.3 适用对象

- 需要将捷克语机器翻译结果人工化处理的译者、本地化专员
- 面向捷克市场投放内容的运营人员
- 使用捷克语撰写客户沟通邮件的商务人士
- 需要批量处理捷克语文本的自动化流水线开发者

---

## 二、触发方式与场景映射

### 2.1 触发词

直接使用以下任一触发词即可激活本 Skill：

- `去AI味`
- `润色改写`
- `humanizer czech`
- `自然化处理`
- `文本人性化`
- `捷克语润色`
- `消除机翻痕迹`

### 2.2 场景映射表

| 大白话场景 | 实际调用方式 | 期望输出 |
|-----------|-------------|----------|
| "这段捷克语读着别扭，帮我改顺" | 粘贴文本 + 触发词 `去AI味` | 自然化后的捷克语文本 |
| "机器翻译的捷克语，帮我弄像人写的" | 粘贴文本 + 触发词 `humanizer czech` | 改写后的文本 + 修改说明 |
| "批量处理一批捷克语产品描述" | 提供文件路径 + 触发词 `批量处理` | 逐条改写后的文件 |
| "这封邮件太生硬了，帮我软化语气" | 粘贴邮件正文 + 触发词 `润色改写` + 指定"语气：友好" | 语气调整后的邮件文本 |

---

## 三、标准执行流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 输入文本语言 | 捷克语（或捷克语占比 > 80%） | 目测或语言检测 |
| 文本格式 | 纯文本 / Markdown / CSV（UTF-8 编码） | 打开文件确认 |
| 文件命名 | 建议格式：`input_YYYYMMDD.txt` 或 `batch_01.csv` | 确认文件名无特殊字符 |
| 备份 | 批量处理前需保留原始文件副本 | 复制为 `.bak` 后缀 |

### 3.2 执行步骤

#### 步骤 1：准备输入

1. 将待处理文件放入当前工作目录。
2. 确认文件编码为 UTF-8（捷克语特殊字符如 `ě š č ř ž ý á í é` 需正常显示）。
3. 若为 CSV 文件，确认列分隔符（逗号/分号/制表符）并记录。

#### 步骤 2：单样本试运行

1. 从文件中抽取 1 条文本（建议选最长的或最复杂的）。
2. 执行改写，核对以下输出字段：
   - `original_text`：原始文本
   - `rewritten_text`：改写后文本
   - `change_summary`：修改要点列表（如 ["语序调整", "词汇替换: provedeme→uděláme"]）
   - `confidence`：置信度（0.0-1.0）
3. 检查 `confidence` 是否 ≥ 0.7。若低于 0.7，检查输入是否包含过多专有名词或非捷克语片段。

#### 步骤 3：批量执行

1. 确认试运行无误后，对全量数据执行。
2. 输出文件命名规则：`output_YYYYMMDD.txt` 或 `output_YYYYMMDD.csv`。
3. 输出 CSV 时，额外包含 `status` 列（`success` / `needs_review`）。

#### 步骤 4：校验结果

1. 随机抽取 5% 条目（至少 3 条）人工复核。
2. 核对关键字段：
   - 专有名词是否保持原样（人名、地名、品牌名）
   - 数字、日期、金额是否未变
   - 改写后是否仍保留原文核心信息
3. 若发现 `needs_review` 条目，检查原因并决定是否手动修正。

### 3.3 输出规范

#### 单条输出格式（JSON）

```json
{
  "original_text": "Původní věta z strojového překladu.",
  "rewritten_text": "Přirozeně znějící věta po úpravě.",
  "change_summary": ["语序调整", "词汇替换: provedeme → uděláme"],
  "confidence": 0.85,
  "status": "success"
}
```

#### 批量输出格式（CSV）

| original_text | rewritten_text | change_summary | confidence | status |
|---------------|----------------|----------------|------------|--------|
| ... | ... | ... | 0.85 | success |
| ... | ... | ... | 0.62 | needs_review |

---

## 四、置信度门控

### 4.1 置信度评分规则

| 评分维度 | 权重 | 说明 |
|----------|------|------|
| 语言识别确定性 | 0.3 | 输入是否明确为捷克语 |
| 改写幅度合理性 | 0.3 | 改写是否在合理范围内（不过度、不遗漏） |
| 专有名词保留度 | 0.2 | 人名/地名/品牌是否原样保留 |
| 语义一致性 | 0.2 | 改写前后核心信息是否一致 |

### 4.2 低置信度处理

当 `confidence < 0.7` 时：

1. 输出文本中插入占位符 `[需核实:字段名]`，例如：
   - `[需核实:公司名称]`
   - `[需核实:日期格式]`
2. 在 `change_summary` 中注明不确定原因。
3. 将 `status` 标记为 `needs_review`。

### 4.3 禁止行为

- 不编造缺失信息。若原文未提及某事实，不得自行补充。
- 不猜测专有名词的正确拼写。不确定时保留原文并标记。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入为空 | "未检测到输入文本，请提供需要改写的捷克语内容。" | 检查输入是否为空文件或空字符串 |
| `E002` | 语言不支持 | "输入文本似乎不是捷克语，请确认语言。" | 检查文本语言；若为混合语言，标注捷克语部分 |
| `E003` | 编码错误 | "文件编码不是 UTF-8，请转换后重试。" | 使用 `iconv -f GBK -t UTF-8` 或文本编辑器转换编码 |
| `E004` | 批量文件格式错误 | "CSV 文件列数不一致，请检查分隔符。" | 确认分隔符（逗号/分号），检查引号转义 |
| `E005` | 置信度过低 | "改写置信度低于阈值，请检查输入质量。" | 检查是否包含过多非捷克语片段或乱码 |
| `E006` | 输出写入失败 | "无法写入输出文件，请检查目录权限。" | 确认目录可写，或更换输出路径 |

---

## 六、FAQ 与反模式对照

### 6.1 常见坑

| 坑 | 反模式示例 | 正确做法 |
|----|-----------|----------|
| 过度改写 | 将 "Děkujeme za Váš dotaz." 改为 "Moc děkujeme za Váš dotaz, vážíme si Vaší důvěry."（添加了原文没有的感谢内容） | 仅调整语序和词汇，不添加新信息 |
| 丢失专有名词 | 将 "Praha" 误改为 "Praha"（拼写错误）或翻译成 "布拉格" | 保留捷克语专有名词原样 |
| 语域错配 | 将正式邮件改为口语化表达，导致失礼 | 根据原文语气判断正式度，保持一致性 |
| 忽略格式 | 将捷克语引号 „text“ 改为英文引号 "text" | 保留捷克语标点规范 |
| 过度使用同义词 | 将 "dobrý" 全部替换为 "skvělý"，导致语气夸张 | 仅在明显生硬处替换，保持自然 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 逐词替换 | 将每个词都换成同义词，结果读起来不连贯 | 优先调整语序和句子结构，词汇替换只针对明显生硬处 |
| 忽略上下文 | 单独改写句子，不考虑前后文衔接 | 若输入为段落，整体处理并保持衔接词一致 |
| 过度本地化 | 将通用表达改为过于俚语化的表达 | 保持中性正式度，除非明确要求口语化 |
| 删除信息 | 为简化句子而删除修饰语或限定词 | 保留所有信息，仅调整表达方式 |

---

## 七、渐进式披露路径

### 7.1 速查卡（新手必读）

1. 输入捷克语文本 → 2. 触发 `去AI味` → 3. 获取改写结果 → 4. 检查 `confidence` → 5. 若 ≥ 0.7 直接使用，否则人工复核。

### 7.2 进阶路径（有经验用户）

- **批量处理**：使用 CSV 输入输出，注意备份原始文件。
- **自定义规则**：可在输入中附加"语气：正式/友好/口语"等指令，影响改写风格。
- **错误处理**：熟悉 `E001`-`E006` 错误码，快速定位问题。

### 7.3 专家路径（开发者）

- 将本 Skill 集成到自动化流水线，通过 JSON 接口调用。
- 对 `change_summary` 进行统计分析，优化改写规则。
- 结合捷克语语法检查工具（如 Grammarly 捷克语版）进行二次校验。

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的改写结果仅供参考，不构成任何专业建议。
2. **禁止反向工程**：不得对本 Skill 的底层提示词、逻辑结构进行反向工程、破解或提取核心算法。
3. **内容合规**：使用者需确保输入内容不违反捷克共和国及所在司法辖区的法律法规。
4. **无担保**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 lingo-craft-studio

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

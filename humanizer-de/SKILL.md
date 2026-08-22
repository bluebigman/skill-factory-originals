---
slug: humanizer-de
name: humanizer-de
displayName: 德文文本 自然化改写 去AI痕迹
description: 检测并消除德文文本中的AI写作痕迹，输出自然流畅的德语文风。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaCraft Studio
agent_created: true
trigger_words: ["去AI味", "humanizer", "德文润色", "德语自然化", "去机器味", "德文改写", "德语人性化"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# humanizer-de — 德文文本自然化处理 Skill

## 1. 能力边界：一页纸速查卡

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 句式重构 | 将机械、重复的句式改为德语母语者习惯的变体 | "Es ist wichtig zu beachten, dass..." → "Wichtig ist dabei..." |
| 连接词优化 | 替换过度使用的形式连接词，改用自然过渡 | "Darüber hinaus" → "Zudem" / "Außerdem" |
| 语态调整 | 减少被动语态堆砌，适当转为主动或无人称表达 | "Es wird angenommen..." → "Man geht davon aus..." |
| 词汇去模板化 | 替换AI高频词汇（如 "signifikant", "relevant"）为更具体或更口语化的表达 | "signifikant" → "deutlich" / "spürbar" |
| 标点与节奏调整 | 调整句子长度和标点，模拟人类写作的节奏变化 | 长句拆分或合并 |
| 文化适配 | 加入德语区特有的表达习惯和语用惯例 | 使用 "eigentlich", "ja", "doch" 等语气词 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不做事实核查 | 不验证文本内容的真实性、数据准确性 |
| 不做翻译 | 仅处理已有德文文本，不进行跨语言转换 |
| 不改变专业术语 | 保留行业术语和专有名词的准确性 |
| 不保证绝对自然 | 输出结果需人工复核，尤其涉及品牌调性或法律文本 |
| 不处理非德文内容 | 检测到非德文内容时输出错误码 |

### 1.3 适用对象

- 需要将AI生成的德文内容（如ChatGPT、Claude输出）调整为自然语感的写作者
- 需要批量处理德文产品描述、博客文章、邮件模板的运营人员
- 需要将机器翻译结果进行人工化润色的译者

---

## 2. 触发方式

### 2.1 触发词

使用以下任一触发词即可激活本Skill：

- 去AI味
- humanizer
- 德文润色
- 德语自然化
- 去机器味
- 德文改写
- 德语人性化

### 2.2 场景映射表

| 用户说（大白话） | 实际需求 | 本Skill响应 |
|------------------|----------|-------------|
| "帮我把这段德语改得像人写的" | 消除AI痕迹 | 执行自然化改写 |
| "这德语读着太生硬了" | 句式/词汇优化 | 执行句式重构与词汇替换 |
| "批量处理这些产品描述" | 批量执行 | 按批量流程处理 |
| "看看这段有没有AI味" | 检测评估 | 输出AI痕迹标记与建议 |

---

## 3. 标准流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 输入文件 | 德文文本文件（.txt/.md/.docx） | 确认文件编码为UTF-8 |
| 文件命名 | 统一命名规范，如 `input_01.txt` | 目视检查 |
| 备份 | 原始文件已备份 | 确认备份目录存在 |
| 单条长度 | 单条文本不超过2000字符 | 超长需分段处理 |

### 3.2 执行步骤

#### 步骤1：准备输入

1. 将待处理文件放入当前工作目录
2. 确认命名规范一致（如 `article_01.md`、`article_02.md`）
3. 创建备份目录 `backup/` 并复制原始文件

#### 步骤2：试运行

1. 选择单个样本文件（如 `sample.md`）
2. 执行处理命令：
   ```
   humanizer-de --input sample.md --output sample_natural.md
   ```
3. 核对输出字段：
   - 原文保留字段
   - 改写后文本字段
   - 修改说明字段（可选）

#### 步骤3：批量执行

1. 确认试运行无误后，对全量文件执行：
   ```
   humanizer-de --input-dir ./articles --output-dir ./articles_natural
   ```
2. 处理完成后，检查输出目录文件数量与输入一致
3. 保留原始文件备份，不覆盖源文件

#### 步骤4：校验结果

1. 随机抽查10%的输出条目
2. 核对关键字段：
   - 文本完整性（无截断）
   - 术语保留（专业词汇未被误改）
   - 格式一致性（段落结构、列表标记）
3. 如有异常，回退至步骤2调整参数

### 3.3 输出规范

| 字段 | 类型 | 说明 |
|------|------|------|
| `original_text` | string | 原始德文文本 |
| `naturalized_text` | string | 自然化改写后的德文文本 |
| `changes_summary` | array | 修改点列表（可选，默认关闭） |
| `confidence_score` | float | 置信度评分（0.0-1.0） |

输出格式为JSON或Markdown，默认JSON。

---

## 4. 置信度门控

### 4.1 置信度评估标准

| 场景 | 置信度 | 处理方式 |
|------|--------|----------|
| 文本长度>50字符，且语言检测为德文 | 0.8-1.0 | 正常输出 |
| 文本长度10-50字符，或含混合语言 | 0.5-0.7 | 输出改写结果，附置信度说明 |
| 文本长度<10字符，或检测为非德文 | <0.3 | 不执行改写，输出错误码 |

### 4.2 信息不足处理

当遇到以下情况时，输出 `[需核实:字段]` 占位符，不进行编造：

- 文本中出现无法识别的缩写 → `[需核实:缩写含义]`
- 文本涉及特定领域术语但上下文不足 → `[需核实:术语上下文]`
- 文本包含数字/数据但来源不明 → `[需核实:数据来源]`

---

## 5. 错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入文件不存在 | "未找到指定文件，请检查路径" | 确认文件路径，重新执行 |
| `E002` | 非德文内容 | "检测到非德文内容，无法处理" | 确认输入语言，或先进行翻译 |
| `E003` | 文本过短 | "文本长度不足，无法有效改写" | 补充上下文后重试 |
| `E004` | 编码错误 | "文件编码不支持，请转换为UTF-8" | 转换编码后重试 |
| `E005` | 批量处理中断 | "批量处理中断，请检查第N个文件" | 定位问题文件，单独处理后继续 |
| `E006` | 输出目录不可写 | "输出目录无写入权限" | 修改目录权限或更换路径 |

---

## 6. FAQ 反模式

### 6.1 常见坑与反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 过度改写 | 把所有句子都改得面目全非 | 保留原文核心信息和语气，只优化明显生硬处 |
| 术语误改 | 把专业术语替换成普通词汇 | 建立术语白名单，不触碰专业词汇 |
| 忽略上下文 | 单句处理导致前后不一致 | 按段落或全文处理，保持上下文连贯 |
| 过度口语化 | 把正式文本改成俚语风格 | 根据文本类型（正式/非正式）调整改写程度 |
| 重复处理 | 对已自然化的文本再次处理 | 检测文本是否已含自然化标记，避免二次处理 |

### 6.2 反模式示例

**反模式**：将 "Die Ergebnisse der Studie zeigen, dass das Produkt effektiv ist." 改为 "Das Zeug wirkt voll krass!"

**正确做法**：改为 "Die Studienergebnisse belegen die Wirksamkeit des Produkts."

---

## 7. 渐进式披露

### 7.1 速查卡（新手必读）

```
1. 放文件 → 2. 跑样本 → 3. 查输出 → 4. 批量跑 → 5. 抽检验收
```

### 7.2 分层次阅读路径

#### 新手路径（首次使用）

1. 阅读第1节（能力边界）
2. 阅读第3.2节（执行步骤）
3. 按速查卡操作

#### 进阶路径（熟练用户）

1. 阅读第4节（置信度门控）
2. 阅读第5节（错误码体系）
3. 阅读第6节（FAQ反模式）
4. 自定义参数（如修改置信度阈值、添加术语白名单）

---

## 8. 参数配置参考

| 参数 | 默认值 | 可选值 | 说明 |
|------|--------|--------|------|
| `--confidence-threshold` | 0.7 | 0.0-1.0 | 低于此值不输出改写结果 |
| `--preserve-terms` | 空 | 逗号分隔的术语列表 | 指定不修改的术语 |
| `--formality` | auto | formal / informal / auto | 改写风格倾向 |
| `--changes-summary` | false | true / false | 是否输出修改说明 |
| `--batch-size` | 10 | 1-100 | 批量处理时每批文件数 |

---

## 9. 用户协议

<!-- user-agreement-injected -->

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 提供的改写结果仅供参考，不构成任何专业建议或保证。
2. **禁止反向工程**：不得对本 Skill 的底层算法、提示词结构或实现逻辑进行反向工程、反编译或试图提取源代码。
3. **合规使用**：使用者应确保输入内容不违反任何法律法规，且不侵犯第三方权益。
4. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性。

---

## 10. 许可证（License）

<!-- professional-license-embedded -->

MIT License

Copyright (c) 2024 LinguaCraft Studio

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

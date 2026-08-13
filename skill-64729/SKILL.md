---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: skill-64729
name: 文本洗稿整理
displayName: 文本洗稿整理 结构化改写 相似度检测
description: 将杂乱文本整理为结构化内容，智能改写并检测相似度。
version: 1.0.1
rules_version: cpr-20260813-n401
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/skill-64729
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林墨研
agent_created: true
trigger_words: ["洗稿", "文本整理", "改写", "结构化", "去重", "内容重组", "段落润色"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# 文本洗稿整理 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入类型 | 纯文本、可提取文字的 PDF（文字版）、TXT、Markdown | 扫描件（需先 OCR）、图片、音频、视频 |
| 处理能力 | 分段、提炼小标题、生成摘要（≤100字）、改写、相似度检测 | 判断是否侵权、提供法律意见、处理非文本内容 |
| 输出形式 | 结构化文本 + 校验报告 | 不保证改写后通过任何特定查重系统 |
| 批量处理 | 支持多篇文本（用 `---` 分隔） | 不支持混合格式批量输入 |

### 1.2 适用对象

- **适用**：需要将口语化、重复、无结构的原始文本整理为规范文章的内容创作者、编辑、运营人员。
- **不适用**：需要法律级版权判断的场景、需要处理图片内文字的场景、需要保证改写后绝对原创的场景。

### 1.3 关键参数速查

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 相似度阈值 | 0.6 | 超过该值触发第二轮改写 |
| 摘要长度 | ≤100字 | 自动生成的内容摘要上限 |
| 段落最小长度 | 20字 | 低于此长度的段落将合并 |
| 批量分隔符 | `---` | 多篇文本的分隔标记 |

---

## 二、触发方式

### 2.1 触发词

- 核心触发词：洗稿、文本整理、改写、结构化、去重
- 补充触发词：内容重组、段落润色、文章优化

### 2.2 场景映射表

| 用户说（大白话） | 实际触发动作 |
|-----------------|-------------|
| "帮我把这段乱七八糟的文字整理一下" | 调用 `read_input()` 读取文本 → `split_paragraphs()` 分段 → `rewrite_text()` 改写 → `calculate_similarity()` 检测 → `generate_report()` 输出 |
| "这篇文章口语太重，帮我改得书面一点" | 同上，改写规则侧重口语→书面转换 |
| "我有三篇文章要一起处理" | 识别 `---` 分隔符，逐篇处理，合并输出 |
| "帮我看看这段有没有抄别人的" | 仅做相似度检测，不做侵权判断 |

---

## 三、标准流程

### 3.1 前置条件

1. 输入文本非空（空输入返回错误码 E001）
2. 输入为纯文本或可提取文字的 PDF
3. 批量输入时，各篇之间用 `---` 单独一行分隔

### 3.2 执行步骤

**步骤 1：读取输入**

调用 `read_input()` 读取文件路径或直接接收文本内容。

```python
def read_input(source):
    """
    读取输入文本
    :param source: 文件路径或直接文本
    :return: 文本内容字符串
    """
    if not source or not source.strip():
        return {"error": "E001", "message": "输入为空"}
    # 读取逻辑...
    return content
```

**步骤 2：分段处理**

调用 `split_paragraphs()` 将文本按语义边界切分为独立段落。

```python
def split_paragraphs(text):
    """
    将文本分段
    :param text: 原始文本
    :return: 段落列表
    """
    # 按空行、句号、问号、感叹号等边界切分
    # 合并过短段落（<20字）
    # 返回段落列表
    return paragraphs
```

**步骤 3：逐段改写**

调用 `rewrite_text()` 对每个段落进行改写。改写规则包括：

| 规则编号 | 规则内容 | 示例 |
|---------|---------|------|
| R1 | 口语词转书面语 | "搞" → "进行/开展" |
| R2 | 删除重复冗余表达 | "非常非常" → "非常" |
| R3 | 被动句转主动句 | "被大家认为" → "大家认为" |
| R4 | 长句拆分（>50字） | 拆为2-3个短句 |
| R5 | 短句合并（<10字且语义相关） | 合并为一个完整句 |
| R6 | 具体数字保留，模糊表达具体化 | "很多人" → "多数受访者"（如有数据支撑） |

**步骤 4：相似度计算**

调用 `calculate_similarity()` 计算改写前后文本的相似度。

```python
def calculate_similarity(original, rewritten):
    """
    计算相似度（基于 Jaccard + 余弦混合算法）
    :param original: 原文段落
    :param rewritten: 改写后段落
    :return: 相似度分数（0.0 - 1.0）
    """
    # 分词 → 计算 Jaccard 相似度
    # 计算 TF-IDF 余弦相似度
    # 取两者加权平均
    return similarity_score
```

**相似度判定规则：**

| 相似度范围 | 处理动作 |
|-----------|---------|
| 0.0 - 0.3 | 通过，无需处理 |
| 0.3 - 0.6 | 通过，记录提示 |
| 0.6 - 0.8 | 触发第二轮改写（增加替换强度） |
| 0.8 - 1.0 | 触发第二轮改写 + 人工复核建议 |

**步骤 5：报告生成**

调用 `generate_report()` 生成校验报告，随结果文件一并输出。

报告包含：
- 每段原文与改写后文本对照
- 相似度评分
- 改写规则命中情况
- 整体统计（总段落数、改写段落数、平均相似度）

### 3.3 输出规范

**输出文件结构：**

```
output/
├── result.md          # 合并后的结构化文本
└── report.json        # 逐篇校验报告
```

**result.md 格式：**

```markdown
# 文章标题（自动提炼）

> 摘要：xxx（≤100字）

## 小标题1
段落内容...

## 小标题2
段落内容...
```

**report.json 格式：**

```json
{
  "article_id": 1,
  "total_paragraphs": 12,
  "rewritten_paragraphs": 10,
  "avg_similarity": 0.42,
  "paragraphs": [
    {
      "index": 1,
      "original": "原文...",
      "rewritten": "改写后...",
      "similarity": 0.35,
      "rules_applied": ["R1", "R3"]
    }
  ]
}
```

---

## 四、置信度门控

### 4.1 信息不足处理

当遇到以下情况时，输出 `[需核实:字段]` 占位符，不编造内容：

| 场景 | 处理方式 |
|------|---------|
| 原文中数据来源不明确 | 输出 `[需核实:数据来源]` |
| 原文引用他人观点但未署名 | 输出 `[需核实:引用出处]` |
| 原文时间信息模糊 | 输出 `[需核实:具体时间]` |
| 原文存在明显逻辑跳跃 | 输出 `[需核实:逻辑衔接]` |

### 4.2 置信度分级

| 置信度等级 | 判定标准 | 输出行为 |
|-----------|---------|---------|
| 高（≥0.8） | 信息完整、来源清晰 | 正常输出 |
| 中（0.5-0.8） | 部分信息缺失 | 输出 + 标注需核实项 |
| 低（<0.5） | 关键信息缺失 | 输出 + 建议补充材料 |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|---------|---------|
| E001 | 输入为空 | "未检测到输入内容，请提供文本或文件路径" | 检查输入参数，重新提交 |
| E002 | 文件不存在 | "指定的文件路径不存在，请确认路径是否正确" | 核对文件路径，确认文件已保存 |
| E003 | 文件格式不支持 | "仅支持纯文本或文字版 PDF 文件" | 转换文件格式，或先进行 OCR |
| E004 | 批量分隔符缺失 | "检测到多篇内容但缺少 `---` 分隔符" | 在每篇文本之间添加 `---` 单独一行 |
| E005 | 段落过短无法处理 | "存在少于20字的段落，已自动合并" | 无需操作，系统自动处理 |
| E006 | 相似度检测失败 | "相似度计算异常，请检查文本编码格式" | 确认文本为 UTF-8 编码，重新提交 |
| E007 | 输出目录无写入权限 | "无法写入输出文件，请检查目录权限" | 更换输出目录或调整权限设置 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 常见坑 | 反模式（错误做法） | 正模式（正确做法） |
|--------|-------------------|-------------------|
| 输入扫描件 PDF | 直接提交扫描件，期望提取文字 | 先使用 OCR 工具提取文字，再提交处理 |
| 批量输入忘记分隔符 | 直接粘贴多篇文章，无 `---` 分隔 | 每篇之间用 `---` 单独一行隔开 |
| 期望改写后绝对原创 | 认为相似度=0 才算成功 | 合理目标是相似度 <0.6，完全重写反而可能丢失原意 |
| 要求判断是否侵权 | 让 Skill 给出法律结论 | 仅参考相似度数据，法律判断咨询专业人士 |
| 输入包含图片 | 在文本中插入图片路径 | 仅提交纯文本内容，图片文字需先提取 |

### 6.2 高频问题

**Q1：改写后语义变了怎么办？**

A：检查改写规则 R4（长句拆分）和 R5（短句合并）是否过度应用。可在输入时标注"保守改写"模式，降低改写强度。

**Q2：相似度一直高于 0.6 怎么办？**

A：系统会自动进行第二轮改写（增加替换强度）。若仍高于 0.6，建议人工介入，检查原文是否存在大量固定搭配或专有名词。

**Q3：批量处理时某篇失败会影响其他篇吗？**

A：不会。每篇独立处理，失败篇目会在报告中标记错误码，其他篇目正常输出。

---

## 七、渐进式披露

### 7.1 速查卡（30秒上手）

```
输入 → 文本或文件路径
分隔 → 多篇用 --- 隔开
输出 → result.md + report.json
阈值 → 相似度 >0.6 自动二次改写
```

### 7.2 分层次阅读路径

**新手路径（首次使用）：**

1. 阅读「能力边界」了解适用范围
2. 阅读「触发方式」了解如何调用
3. 阅读「标准流程」步骤 1-3 了解基本操作
4. 遇到问题查阅「错误码体系」

**进阶路径（深度使用）：**

1. 阅读「标准流程」全部步骤，理解改写规则细节
2. 阅读「置信度门控」了解信息处理机制
3. 阅读「FAQ 反模式」避免常见错误
4. 根据 report.json 调整改写策略

---

## 八、使用示例

### 8.1 单篇处理示例

**输入：**

```
今天我去开会了，然后呢，会上讨论了很多事情。然后就是关于新项目的那个事情，大家讨论了很久很久。最后决定下个月开始做。然后还有就是预算的问题，也讨论了一下。
```

**处理过程：**

1. 分段：识别为 3 个语义段落
2. 改写：应用 R1（口语转书面）、R2（删除冗余）、R4（长句拆分）
3. 相似度检测：0.45，通过
4. 生成报告

**输出：**

```markdown
# 项目会议纪要

> 摘要：会议讨论了新项目启动时间及预算安排，决定下月启动。

## 新项目讨论
今日召开项目会议，重点讨论新项目相关事宜。与会人员就项目启动时间进行充分交流，最终确定于下月正式启动。

## 预算安排
会议同时就项目预算问题进行探讨，相关细节有待进一步确认。
```

### 8.2 批量处理示例

**输入：**

```
第一篇文章内容...

---

第二篇文章内容...

---

第三篇文章内容...
```

**输出：**

- `result.md`：包含三篇结构化文本
- `report.json`：包含三篇的独立校验报告

---

## 九、技术实现参考

### 9.1 核心函数接口

```python
# 主流程
def process_article(text):
    paragraphs = split_paragraphs(text)
    results = []
    for para in paragraphs:
        rewritten = rewrite_text(para)
        similarity = calculate_similarity(para, rewritten)
        if similarity > 0.6:
            rewritten = rewrite_text(para, intensity="high")
            similarity = calculate_similarity(para, rewritten)
        results.append({
            "original": para,
            "rewritten": rewritten,
            "similarity": similarity
        })
    return generate_report(results)

# 改写规则实现
def rewrite_text(text, intensity="normal"):
    # R1: 口语词替换表
    oral_to_written = {
        "搞": "进行",
        "弄": "处理",
        "特别特别": "非常",
        "然后": "随后",
        "就是说": "即"
    }
    # R2: 冗余删除
    # R3: 被动转主动
    # R4: 长句拆分
    # R5: 短句合并
    # R6: 模糊表达具体化
    return rewritten_text

# 相似度计算
def calculate_similarity(original, rewritten):
    # Jaccard + 余弦混合
    return score
```

### 9.2 参数调优建议

| 场景 | 建议参数 |
|------|---------|
| 新闻稿改写 | 相似度阈值 0.5，保守改写 |
| 学术文本整理 | 相似度阈值 0.7，保留专业术语 |
| 口语转书面 | 相似度阈值 0.4，激进改写 |
| 技术文档 | 相似度阈值 0.6，保留代码和专有名词 |

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于内容合规性、版权风险、法律纠纷等。
2. **禁止反向工程**：不得对本 Skill 的底层算法、提示词结构、评分逻辑进行反向工程、破解、篡改或二次分发。
3. **合法用途**：本 Skill 仅可用于合法目的，不得用于规避学术诚信审查、恶意抄袭、侵犯他人知识产权等行为。
4. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性。

<!-- user-agreement-injected -->

---

## 许可证（License）

### MIT License

Copyright (c) 2026 林墨研

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

<!-- professional-license-embedded -->

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*

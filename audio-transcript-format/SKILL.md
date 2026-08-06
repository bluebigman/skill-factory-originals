---
slug: audio-transcript-format
name: audio-transcript-format
displayName: 语音转写 文本整理 排版优化
description: 将口语化语音转写稿整理为结构化、可读性强的正式文本。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 文本工坊
agent_created: true
trigger_words: ["音频转写格式化", "转写文本整理", "语音转文字排版", "访谈记录整理", "会议纪要优化", "语音稿润色", "口述整理"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# 语音转写文本整理 Skill 使用指南

## 一、能力边界（一页纸速查卡）

### 本 Skill 能做什么

| 编号 | 处理能力 | 输入示例 | 输出示例 |
|------|----------|----------|----------|
| 1 | 删除语气词（嗯、啊、呃、哦、哎等） | "嗯，我觉得这个方案可以" | "我觉得这个方案可以" |
| 2 | 删除重复词 | "我们我们明天开会" | "我们明天开会" |
| 3 | 删除自我修正前缀 | "不对不对，我说的是周三，周三下午" | "周三下午" |
| 4 | 删除高频口头禅 | "你懂我意思吧，这个需求很急，你懂我意思吧" | "这个需求很急" |
| 5 | 合并碎片化短句 | "然后呢。就是。那个。我们走了。" | "然后我们走了。" |
| 6 | 规范标点符号 | 全角/半角混用、缺失标点 | 统一为全角标点，句子完整 |
| 7 | 段落重排 | 按语义切分或合并段落 | 逻辑清晰、层次分明的段落结构 |
| 8 | 标记不确定信息 | 人名、数字、专有名词听不清 | 输出 `[需核实:人名]` 占位符 |

### 本 Skill 不能做什么

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不补充缺失信息 | 说话人未提及的内容不会自行脑补 |
| 2 | 不改变原意 | 只做格式整理，不做内容增删或观点修改 |
| 3 | 不翻译语言 | 不提供中英互译或其他语言转换 |
| 4 | 不识别说话人身份 | 除非输入中已标注，否则不自动区分发言人 |
| 5 | 不生成摘要 | 只整理全文，不提炼要点（如需摘要请另行说明） |

### 适用对象

- 播客节目逐字稿整理
- 访谈记录文本化
- 会议录音转写稿优化
- 口述历史/回忆录素材整理
- 任何需要将口语转为书面语的场景


## 许可证（License）

```text
MIT License

Copyright (c) {year} {holder}

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

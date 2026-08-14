---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: generate-subtitles
name: generate-subtitles
displayName: 字幕生成 翻译转录 时间轴对齐
description: 将视频、音频或文本稿转换为带时间轴的字幕文件，支持翻译与格式定制。
version: 1.0.1
rules_version: cpr-20260814-n426
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/generate-subtitles
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["视频字幕","generate subtitles","字幕生成","字幕翻译","转录","时间轴对齐","subtitle generation","caption creation"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 字幕生成与翻译处理 Skill 文档

## 一、能力边界速查卡

本 Skill 面向需要将语音或文本内容转换为字幕文件的个人开发者、内容创作者、本地化专员及教育工作者。它提供一套从原始素材到成品字幕的结构化处理路径。

### 能做（核心能力）

| 编号 | 能力项 | 说明 | 输入示例 | 输出示例 |
|------|--------|------|----------|----------|
| 1 | 数据源解析 | 接受文本、SRT/VTT 文件路径或公开 URL | `./meeting_notes.txt`、`https://example.com/a.srt` | 解析后的纯文本内容 |
| 2 | 关键信息识别 | 自动提取说话人、时间码、术语、数字等要素 | 一段含时间戳的对话记录 | 结构化字段列表 |
| 3 | 字幕格式生成 | 按 SRT、VTT、ASS 或纯文本输出 | 处理后的文本块 | 带序号与时间轴的标准 SRT 内容 |
| 4 | 置信度标注 | 对自动识别或翻译结果给出可信度评估 | 机器翻译的句子 | `[高置信]`、`[中置信]`、`[需核实:原文]` |
| 5 | 批量与自定义 | 支持多文件循环处理及输出模板定制 | 目录下 20 个 `.txt` 文件 | 对应 20 个 `.srt` 文件 |

### 不能做（明确边界）

- 不执行语音转文字的底层声学识别（需用户提供文本或外部 ASR 结果）。
- 不保证翻译的文学性，仅提供语义通顺的直译参考。
- 不处理加密、DRM 保护或非法获取的媒体内容。
- 不自动修正源文件中的错别字或逻辑错误，仅做格式与结构处理。

### 适用对象

- 需要为课程视频快速生成中文字幕的教师。
- 需要将播客转录稿转为可发布字幕的播客主。
- 需要为短视频添加双语字幕的剪辑师。
- 需要批量整理会议录音文本的行政人员。

---

## 二、触发方式与场景映射

当你的请求包含以下关键词或意图时，本 Skill 将被激活：

| 用户可能说（大白话） | 触发词命中 | 实际执行动作 |
|----------------------|------------|--------------|
| “帮我把这段采访稿做成字幕文件” | 视频字幕、转录 | 解析文本 → 分段 → 生成 SRT |
| “这个视频的英文台词能翻译成中文吗” | 字幕翻译 | 读取文本 → 翻译 → 输出双语 SRT |
| “我有一堆 txt 文件，想统一转成字幕” | 批量处理、generate subtitles | 遍历目录 → 逐文件转换 → 汇总输出 |
| “字幕时间轴对不上，帮我调整” | 时间轴对齐 | 读取时间码 → 按偏移量修正 → 重写文件 |
| “测试一下这个技能是否正常” | --selftest | 运行内置自检流程，输出版本与状态 |

---

## 三、标准处理流程

### 前置条件

1. 确认输入素材格式受支持（`.txt`、`.srt`、`.vtt`、`.ass` 或公开 URL）。
2. 若输入为视频/音频文件，需先自行完成语音转写，得到文本稿。
3. 将待处理的多个文件放入同一工作目录，并保持命名前缀一致（如 `ep01_raw.txt`、`ep02_raw.txt`）。
4. 明确输出格式需求（默认 SRT，可选 VTT/ASS/纯文本）。

### 执行步骤（分步编号）

1. **素材接收与校验**
   - 检查文件是否存在、是否可读。
   - 若为 URL，先下载至临时目录并校验内容类型。
   - 记录文件编码（UTF-8 无 BOM 为佳）。

2. **内容解析与分段**
   - 按空行或标点符号将文本切分为语义完整的块。
   - 每块预估时长：中文按每秒 4 字、英文按每秒 3 词估算。
   - 生成时间轴：起始时间从 00:00:00,000 开始，按预估时长顺延。

3. **关键信息提取与标注**
   - 识别并保留：说话人标签（若存在）、数字、专有名词、括号注释。
   - 对机器翻译或自动分段的结果，评估一致性，标注置信度。

4. **格式组装**
   - 按所选格式模板填充内容。
   - SRT 模板示例：
     ```
     1
     00:00:01,000 --> 00:00:04,000
     你好，欢迎观看本视频。
     ```
   - VTT 需在文件头添加 `WEBVTT` 声明。

5. **输出与自查**
   - 生成文件至指定输出目录。
   - 自查清单：
     - [ ] 序号连续无跳号
     - [ ] 时间轴无重叠且顺序递增
     - [ ] 文本无截断或乱码
     - [ ] 置信度标注已添加（若适用）

6. **二次确认**
   - 若输入信息不足（如缺少说话人信息、文本过短），主动向用户提问确认。
   - 若批量处理中某文件失败，记录错误并继续，最后汇总报告。

### 输出规范

- 文件命名：`原文件名.输出格式`（如 `meeting_notes.srt`）。
- 字符编码：UTF-8。
- 换行符：LF（Unix 风格）。
- 时间轴格式：`HH:MM:SS,mmm`（SRT）或 `HH:MM:SS.mmm`（VTT）。

---

## 四、置信度门控机制

当处理过程中出现以下情况时，不得强行编造数据：

| 场景 | 处理方式 | 输出占位符 |
|------|----------|------------|
| 某句翻译不确定 | 保留原文，标注待核实 | `[需核实:原文]` |
| 时间轴无法准确估算 | 使用平均语速估算，标注低置信 | `[低置信:时间轴]` |
| 说话人身份不明 | 不猜测，标注未知 | `[需核实:说话人]` |
| 专有名词拼写存疑 | 保留原样，标注 | `[需核实:拼写]` |

**原则：宁可明确标注不确定性，也不提供虚假的精确结果。**

---

## 五、错误码体系

| 错误码 | 含义 | 用户提示话术 | 修正步骤 |
|--------|------|--------------|----------|
| `E001` | 文件不存在或路径错误 | “未找到指定文件，请检查路径是否正确。” | 1. 确认路径 2. 检查文件名大小写 3. 重新输入 |
| `E002` | 格式不支持 | “该文件格式不在支持列表内，请转换为 txt/srt/vtt/ass。” | 1. 转换格式 2. 重新提交 |
| `E003` | 内容为空 | “文件内容为空，无法生成字幕。” | 1. 检查源文件 2. 补充内容后重试 |
| `E004` | 时间轴重叠 | “检测到时间轴重叠，请检查源文本分段。” | 1. 自动调整重叠段 2. 或手动指定分段点 |
| `E005` | 批量处理中断 | “批量处理在第 N 个文件处中断，错误信息：...” | 1. 查看错误详情 2. 修复后从断点继续 |
| `E006` | 编码异常 | “文件编码无法识别，请另存为 UTF-8 格式。” | 1. 用文本编辑器转换编码 2. 重新提交 |

---

## 六、FAQ 与反模式对照

| 常见坑（反模式） | 问题描述 | 正确做法（模式） |
|------------------|----------|------------------|
| 忽略置信度标注 | 直接输出机器翻译结果，不提示不确定性 | 对低置信内容显式标注 `[需核实]` |
| 时间轴一刀切 | 所有句子按固定 3 秒切分，导致长句被截断 | 根据字数/词数动态估算时长 |
| 批量处理不备份 | 直接覆盖原始文件，出错后无法恢复 | 处理前复制原始文件至 `./backup/` |
| 不校验编码 | 输出文件在播放器中显示乱码 | 统一使用 UTF-8 编码并声明 |
| 过度承诺 | 声称“翻译绝对准确” | 说明翻译为参考性质，建议人工复核 |

---

## 七、渐进式披露阅读路径

### 新手快速上手（3 分钟）

1. 准备一个 `.txt` 文本稿。
2. 调用本 Skill，输入文件路径。
3. 接收生成的 `.srt` 文件，直接拖入播放器查看效果。

### 进阶用户完整控制（10 分钟）

1. 阅读「标准处理流程」章节，理解分段与时间轴估算逻辑。
2. 自定义输出模板（如 ASS 格式带样式）。
3. 使用批量模式处理整个目录。
4. 结合置信度标注，人工复核机器翻译结果。

### 高级定制（30 分钟）

1. 修改时间轴估算参数（语速系数）。
2. 集成外部术语表，提升专有名词识别率。
3. 编写后处理脚本，自动修正常见标点问题。

---

## 八、命令行接口说明

本 Skill 支持以下 CLI 参数：

| 参数 | 说明 | 示例 |
|------|------|------|
| `--selftest` | 运行内置自检，验证环境与依赖 | `generate-subtitles --selftest` |
| `--version` | 输出版本号 | `generate-subtitles --version` |

自检内容包括：文件读写权限、时间轴计算函数、格式模板完整性。

---

## 九、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 仅提供技术处理流程，不涉及内容合法性与版权审查。
2. **合法用途**：本 Skill 仅供学习、研究与个人参考使用。请勿用于侵犯他人知识产权、隐私权或任何违反适用法律的活动。
3. **禁止反向工程**：不得对本 Skill 的提示词、内部逻辑进行反向工程、破解或二次分发以规避任何限制。
4. **无担保**：本 Skill 按“现状”提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性。
5. **内容免责**：用户输入的内容及输出结果，其准确性与合法性由用户自行判断。本 Skill 不对翻译质量、时间轴精确性作绝对保证。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

本 Skill 采用 MIT 许可证发布。

```
MIT License

Copyright (c) 2026 原创作者（自持版权）

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证适用性。*

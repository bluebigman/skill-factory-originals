---
slug: generate-subtitles
name: generate-subtitles
displayName: 字幕工坊 时间轴生成 多格式输出
description: 将音视频或文稿转为带时间轴字幕，支持翻译与格式定制。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 流萤工具箱
agent_created: true
trigger_words: ["视频字幕", "generate subtitles", "字幕生成", "字幕翻译", "转录", "字幕制作", "时间轴对齐"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# SKILL.md — 字幕工坊（generate-subtitles）

## 一、能力边界速查卡

本 Skill 负责把「语音或文字」变成「带时间轴的字幕文件」。先看清边界，避免误用。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入格式 | `.txt`、`.srt`、`.vtt`、`.ass`、公开可访问的媒体 URL | 本地加密文件、需登录的网盘链接、非公开 URL |
| 媒体处理 | 从视频/音频中提取语音并转写为文本 | 无法处理无声视频、纯音乐无语音内容 |
| 输出格式 | SRT（默认）、VTT、ASS、纯文本 | 不输出加密格式或专有播放器格式 |
| 翻译能力 | 基于转写文本进行机器翻译（多语种） | 不保证翻译文学质量，不替代专业人工翻译 |
| 批量处理 | 同一目录下多个文件，命名前缀一致即可批量 | 不处理跨目录散乱文件 |
| 时间轴 | 基于语速系数估算时间轴，支持参数调整 | 无法做到逐帧级精确对齐（需人工微调） |

**适用对象**：视频创作者、课程制作人、播客运营者、需要为视频添加字幕的普通用户。

**不适用对象**：需要广播级精确字幕的专业字幕组、需要法律效力翻译的正式文件。

---

## 二、触发方式与场景映射

当你的表达中出现以下意图时，本 Skill 会被激活：

| 大白话说法 | 触发词命中 | 实际执行内容 |
|------------|-----------|-------------|
| "帮我把这个视频加上字幕" | 视频字幕 | 提取语音→转写→生成 SRT |
| "这段录音能转成文字吗" | 转录 | 语音转写为纯文本 |
| "字幕翻成英文" | 字幕翻译 | 转写后执行机器翻译 |
| "给我做个带样式的字幕" | 字幕生成 | 输出 ASS 格式带基础样式 |
| "批量处理这几集字幕" | generate subtitles | 目录扫描+批量生成 |

---

## 三、标准处理流程

### 前置条件

1. 确认输入文件存在且格式受支持（见能力边界表）。
2. 若输入为视频/音频，确保文件可正常解码（无损坏）。
3. 若需批量处理，将所有文件放入同一目录，命名前缀一致（如 `ep01_raw.mp4`、`ep02_raw.mp4`）。
4. 明确输出格式需求（默认 SRT，可选 VTT/ASS/纯文本）。

### 执行步骤

**步骤 1：素材接收与校验**

- 检查文件扩展名是否在支持列表内。
- 若为 URL，先验证可访问性（HTTP 状态码 200）。
- 校验文件大小：单个文件不超过 2GB，文本文件不超过 50MB。

**步骤 2：内容解析与分段**

- 若输入为媒体文件，先执行语音转写（Whisper 类模型），得到带时间戳的文本稿。
- 若输入为纯文本，按语义段落切分，每段约 50-80 字（中文）或 100-150 词（英文）。
- 分段规则：以句号、问号、感叹号作为硬断点；逗号、分号作为软断点，软断点处若超过最大长度也强制断开。

**步骤 3：关键信息提取与标注**

- 识别说话人（若音频含多说话人，标注 `[说话人A]` 前缀）。
- 标记非语音内容（如 `[音乐]`、`[掌声]`、`[笑声]`）。
- 对机器翻译结果附加置信度评分（0-1），低于 0.6 的片段标注 `[需人工复核]`。

**步骤 4：格式组装**

- 按目标格式模板组装字幕块。
- SRT 模板：
  ```
  序号
  起始时间 --> 结束时间
  字幕文本
  （空行）
  ```
- 时间轴格式：`HH:MM:SS,mmm`（SRT）或 `HH:MM:SS.mmm`（VTT）。
- ASS 格式额外包含样式头（字体、字号、颜色、位置）。

**步骤 5：输出与自查**

- 生成文件后执行以下检查：
  - 时间轴是否单调递增（无倒序）。
  - 相邻字幕间隔是否 ≥ 50ms（避免闪烁）。
  - 文本是否包含未替换的占位符。
  - 文件编码是否为 UTF-8（避免乱码）。

**步骤 6：二次确认**

- 输出文件清单及每个文件的字幕条数、总时长。
- 提示用户抽查 3-5 个时间点，确认对齐精度。
- 若用户反馈偏差，调整语速系数（默认 4.5 字/秒，可调范围 3.0-6.0）后重新生成。

### 输出规范

- 输出文件命名：`{原文件名}_subtitled.{ext}`（如 `ep01_raw_subtitled.srt`）。
- 输出目录：默认与输入同目录，可通过参数指定。
- 附带一份 `report.json`，包含处理统计（文件数、总时长、字幕条数、平均置信度）。

---

## 四、置信度门控

本 Skill 遵循「不编造」原则。以下情况输出占位符而非虚构内容：

| 场景 | 输出内容 |
|------|---------|
| 语音转写中某段无法识别 | `[听不清]` |
| 翻译置信度低于 0.6 | `[需核实:原文片段]` + 原文 |
| 说话人无法区分 | `[未知说话人]` |
| 时间轴估算超出合理范围 | `[需核实:时间戳]` |

占位符不会被静默替换。用户需人工确认后，占位符才会被实际内容替代。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|---------|---------|
| `E001` | 文件不存在 | "未找到指定文件，请检查路径" | 确认路径正确后重试 |
| `E002` | 格式不支持 | "该文件格式不在支持列表内" | 转换为 `.txt`/`.srt`/`.vtt`/`.ass` 后重试 |
| `E003` | URL 不可访问 | "无法访问该链接，请确认公开性" | 下载到本地后重试 |
| `E004` | 媒体解码失败 | "视频/音频解码失败，文件可能损坏" | 用播放器验证文件完整性 |
| `E005` | 无语音内容 | "未检测到语音，请确认文件内容" | 更换素材或检查音轨 |
| `E006` | 批量命名不一致 | "批量模式要求文件名前缀一致" | 统一重命名后重试 |
| `E007` | 输出目录无权限 | "无法写入输出目录" | 更换目录或调整权限 |

---

## 六、常见坑与反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|---------|
| 时间轴漂移 | 直接使用默认语速系数不调整 | 先处理 1 分钟样本，对比实际语速后调整系数 |
| 翻译质量差 | 直接发布机器翻译结果 | 人工复核置信度低于 0.7 的片段 |
| 批量处理混乱 | 不同集数文件混放同一目录 | 按集数分目录，或统一命名前缀 |
| 特殊名词错误 | 不做任何预处理直接转写 | 先提供术语表（人名、地名、产品名） |
| 格式兼容问题 | 输出 ASS 但播放器不支持 | 确认目标播放器支持的格式后再输出 |

---

## 七、渐进式披露路径

### 新手路径（5 分钟上手）

1. 阅读「能力边界速查卡」确认需求匹配。
2. 准备一个 `.txt` 文本稿。
3. 调用本 Skill，输入文件路径。
4. 接收生成的 `.srt` 文件，直接拖入播放器查看效果。

### 进阶路径（深度定制）

1. 阅读「标准处理流程」章节，理解分段与时间轴估算逻辑。
2. 自定义输出模板（如 ASS 格式带样式）。
3. 使用批量模式处理整个目录。
4. 结合置信度标注，人工复核机器翻译结果。

### 专家路径（参数调优）

1. 修改时间轴估算参数（语速系数）。
2. 集成外部术语表，提升专有名词识别率。
3. 编写后处理脚本，自动修正常见标点问题。

---

## 八、参数参考表

| 参数名 | 默认值 | 取值范围 | 说明 |
|--------|--------|---------|------|
| `speed_factor` | 4.5 | 3.0-6.0 | 中文语速（字/秒），影响时间轴估算 |
| `max_line_length` | 60 | 20-100 | 单条字幕最大字符数 |
| `min_gap_ms` | 50 | 20-200 | 相邻字幕最小间隔（毫秒） |
| `confidence_threshold` | 0.6 | 0.0-1.0 | 低于此值的翻译标注需复核 |
| `output_format` | srt | srt/vtt/ass/txt | 输出格式 |
| `batch_mode` | false | true/false | 是否启用批量处理 |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即视为同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。本 Skill 仅提供技术处理流程，不涉及内容合法性与版权审查。

2. **合法用途**：本 Skill 仅供学习、研究与个人参考使用。请勿用于侵犯他人知识产权、隐私权或任何违反适用法律的活动。

3. **禁止反向工程**：不得对本 Skill 的提示词、内部逻辑进行反向工程、破解或二次分发以规避任何限制。

4. **无担保**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性。

5. **内容免责**：用户输入的内容及输出结果，其准确性与合法性由用户自行判断。本 Skill 不对翻译质量、时间轴精确性作绝对保证。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 流萤工具箱

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

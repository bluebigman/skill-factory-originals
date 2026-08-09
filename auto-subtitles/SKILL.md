---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: auto-subtitles
name: auto-subtitles
displayName: 视频字幕 本地转写 语音识别
description: 本地AI语音识别，将视频音频快速转为字幕与文本。
version: 1.0.1
rules_version: cpr-20260809-n251
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/auto-subtitles
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["auto-subtitles", "字幕生成", "语音转写", "视频字幕", "音频转文本", "字幕制作", "本地转写"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# auto-subtitles 技能文档

## 一、能力边界速查卡

本技能面向需要从视频或音频文件中提取文字内容的场景，利用本地 AI 语音识别引擎（faster-whisper）完成转写，并输出为字幕或纯文本文件。

### 能做与不能做

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入 | 本地视频文件（mp4/mkv/mov/avi 等）、本地音频文件（mp3/wav/flac/m4a 等）、可访问的媒体 URL | 无法处理加密流媒体、DRM 保护内容、实时直播流 |
| 处理 | 自动检测语言、生成带时间戳的字幕（SRT/VTT）、输出纯文本、批量处理多个文件 | 不支持说话人分离（diarization）、不支持实时流式转写 |
| 输出 | SRT 字幕文件、VTT 字幕文件、TXT 纯文本、JSON 结构化结果（含置信度） | 不执行翻译、不进行语义摘要、不修正原音频中的口误 |
| 环境 | 本地运行，无需联网（模型首次下载除外） | 不依赖云端 API，但需要本地有足够的 CPU/内存资源 |

### 适用对象

- 需要为课程视频、会议录音、采访素材快速生成字幕的内容创作者
- 需要将音频档案转成可检索文本的研究人员
- 希望在不上传隐私内容到云端的前提下完成转写的个人用户

### 不适用对象

- 需要多说话人区分标注的专业会议记录场景
- 需要高精度领域术语识别的医疗/法律等专业场景（需额外微调模型）
- 对转写速度要求高于准确率的实时场景

---

## 二、触发方式与场景映射

当你的指令中出现以下关键词或含义时，本技能将被激活：

| 触发词/短语 | 典型用户表述 | 技能响应 |
|-------------|--------------|----------|
| auto-subtitles | "用 auto-subtitles 给这个视频加字幕" | 启动完整转写流程 |
| 字幕生成 | "帮我生成字幕文件" | 启动完整转写流程 |
| 语音转写 | "把这段录音转成文字" | 启动完整转写流程 |
| 视频字幕 | "给这个 mp4 配上字幕" | 启动完整转写流程 |
| 音频转文本 | "这个播客能转成文本吗" | 启动完整转写流程 |
| 字幕制作 | "我要给采访视频做字幕" | 启动完整转写流程 |
| 本地转写 | "不用联网能转写吗" | 启动完整转写流程并说明本地处理特性 |

**补充触发词**：语音识别、听写、字幕文件、transcribe、subtitle generation

---

## 三、标准执行流程

### 前置条件

1. 确认目标媒体文件存在且格式受支持（ffmpeg 可解码的格式均可）
2. 确认本地已安装 faster-whisper 库（`pip install faster-whisper`）
3. 确认有足够的磁盘空间存放模型文件（首次运行需下载约 150MB-3GB 模型）
4. 确认 CPU 支持 AVX 指令集（2011 年后的主流处理器均满足）

### 执行步骤

**步骤 1：输入确认**

接收用户提供的文件路径或 URL。若为 URL，先下载到本地临时目录。确认文件可读且非空。

```bash
# 检查文件有效性
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 input.mp4
```

**步骤 2：参数配置**

根据用户需求设定转写参数：

| 参数 | 默认值 | 可选值 | 说明 |
|------|--------|--------|------|
| model_size | small | tiny/base/small/medium/large-v3 | 模型越大准确率越高，速度越慢 |
| language | auto | 具体语言代码（如 zh/en/ja） | 自动检测或指定语言 |
| output_format | srt | srt/vtt/txt/json | 输出文件格式 |
| beam_size | 5 | 1-10 | 束搜索宽度，越大越准但越慢 |
| word_timestamps | false | true/false | 是否输出词级时间戳 |

**步骤 3：执行转写**

调用 faster-whisper 完成识别：

```python
from faster_whisper import WhisperModel

model = WhisperModel("small", device="cpu", compute_type="int8")
segments, info = model.transcribe("input.mp4", beam_size=5)

for segment in segments:
    print(f"[{segment.start:.2f} -> {segment.end:.2f}] {segment.text}")
```

**步骤 4：生成输出文件**

根据 output_format 参数生成对应文件：

- **SRT 格式**：标准字幕格式，含序号、时间轴、文本
- **VTT 格式**：Web 字幕格式，兼容 HTML5 视频播放器
- **TXT 格式**：纯文本，仅包含转写文字
- **JSON 格式**：结构化数据，含每段的时间戳、文本、置信度

**步骤 5：结果校验**

检查输出文件是否完整生成，时间轴是否连续，文本是否为空。若检测到大量低置信度片段（置信度 < 0.5），在结果中标注提示。

### 输出规范

所有输出文件命名规则：`原文件名_语言_模型尺寸.扩展名`

示例：`interview_zh_small.srt`

---

## 四、置信度门控机制

本技能在以下情况会输出 `[需核实:字段]` 占位符，而非编造内容：

| 场景 | 处理方式 |
|------|----------|
| 音频质量极差（背景噪音过大） | 在输出中标注 `[需核实:音频质量]`，并建议用户降噪后重试 |
| 检测到多种语言混合 | 标注 `[需核实:语言切换]`，列出检测到的语言及对应时间段 |
| 专有名词/人名识别不确定 | 标注 `[需核实:专有名词]`，给出最可能的拼写 |
| 模型置信度低于 0.4 的片段 | 在 JSON 输出中标记 `"confidence": 0.35, "needs_review": true` |

**置信度分级说明**：

- 0.8-1.0：高置信度，可直接使用
- 0.6-0.8：中等置信度，建议人工校对
- 0.4-0.6：低置信度，需要人工重听
- < 0.4：极低置信度，输出占位符并提示

---

## 五、错误码体系

| 错误码 | 错误描述 | 用户提示话术 | 修正步骤 |
|--------|----------|--------------|----------|
| E001 | 文件不存在或路径错误 | "未找到指定文件，请检查路径是否正确" | 确认文件路径，使用绝对路径或正确相对路径 |
| E002 | 文件格式不支持 | "该文件格式无法解码，请转换为 mp4/mp3/wav 等常见格式" | 使用 ffmpeg 转换格式后重试 |
| E003 | 模型加载失败 | "语音识别模型加载失败，请检查网络连接或模型完整性" | 重新下载模型，或更换模型尺寸 |
| E004 | 内存不足 | "处理过程中内存不足，请关闭其他程序或使用更小的模型" | 切换至 tiny/base 模型，或分批处理 |
| E005 | 音频时长过短 | "音频时长过短（<1秒），无法进行有效识别" | 提供更长的音频片段 |
| E006 | 输出目录无写入权限 | "无法写入输出文件，请检查目录权限" | 更换输出目录或修改权限 |
| E007 | 语言检测失败 | "无法自动检测语言，请手动指定语言代码" | 使用 language 参数指定语言 |
| E008 | 批量处理中断 | "批量处理在第 N 个文件时中断，请检查该文件是否损坏" | 单独处理出错文件，或跳过继续 |

---

## 六、FAQ 与反模式对照

### 常见坑位

**坑 1：追求绝对准确率**

反模式：用户期望 100% 准确的转写结果。
正确认知：语音识别受音频质量、口音、专业术语影响，准确率通常在 85%-98% 之间。建议对关键内容进行人工校对。

**坑 2：忽略模型选择**

反模式：所有文件都用 large-v3 模型，导致处理极慢。
正确做法：短音频（<5分钟）用 small/base 即可；长音频（>1小时）用 medium；对准确率要求极高的场景才用 large-v3。

**坑 3：不处理背景噪音**

反模式：直接转写有大量背景噪音的录音，结果质量差。
正确做法：先使用 ffmpeg 降噪（`ffmpeg -i input.wav -af afftdn=nr=12 output.wav`），再进行转写。

**坑 4：忽略时间戳精度**

反模式：使用默认参数，导致字幕与画面不同步。
正确做法：开启 word_timestamps=true 获得词级时间戳，或使用 beam_size=10 提高时间轴精度。

**坑 5：批量处理不设断点**

反模式：一次性提交 100 个文件，中途失败需全部重来。
正确做法：分批处理（每批 10-20 个），记录已完成列表，支持断点续传。

### 反模式对照表

| 反模式 | 推荐替代方案 |
|--------|--------------|
| 盲目使用最大模型 | 根据音频时长和准确率需求选择合适模型 |
| 忽略置信度信息 | 利用 JSON 输出中的置信度字段定位需校对片段 |
| 不检查输出文件 | 转写完成后抽查首中尾三段，确认时间轴和文本正确 |
| 覆盖原始文件 | 始终保留原始媒体文件，输出文件单独存放 |

---

## 七、渐进式披露路径

### 速查卡（30 秒上手）

```
输入：视频/音频文件路径
命令：auto-subtitles --input file.mp4 --output_format srt
输出：同目录下生成 .srt 字幕文件
```

### 新手路径（首次使用）

1. 安装依赖：`pip install faster-whisper ffmpeg-python`
2. 运行基础命令生成字幕
3. 打开生成的 SRT 文件，确认内容正确
4. 如有问题，参考错误码表排查

### 进阶路径（深度使用）

1. 学习调整 beam_size、model_size 参数平衡速度与准确率
2. 使用 JSON 输出格式，结合置信度字段开发校对工作流
3. 编写批处理脚本，结合 ffmpeg 完成降噪、分段、转写全流程
4. 探索不同语言模型的适用场景，建立自己的参数配置库

### 专家路径（定制开发）

1. 修改 faster-whisper 源码，集成自定义词汇表
2. 开发 Web 界面，提供可视化校对功能
3. 结合向量数据库，构建音视频内容的语义检索系统

---

## 八、技术参数参考

### 模型尺寸与资源消耗

| 模型 | 参数量 | 内存需求 | 相对速度 | 相对准确率 |
|------|--------|----------|----------|------------|
| tiny | 39M | ~1GB | 32x | 较低 |
| base | 74M | ~1GB | 16x | 中等 |
| small | 244M | ~2GB | 6x | 较高 |
| medium | 769M | ~5GB | 2x | 高 |
| large-v3 | 1550M | ~10GB | 1x | 最高 |

### 支持的语言

faster-whisper 支持 99 种语言的自动检测与转写，包括中文（zh）、英文（en）、日文（ja）、韩文（ko）、法文（fr）、德文（de）、西班牙文（es）等。指定语言代码可提高识别速度和准确率。

### 输出格式示例

**SRT 格式**：
```
1
00:00:00,000 --> 00:00:03,500
大家好，欢迎观看本期视频。

2
00:00:03,500 --> 00:00:07,200
今天我们来讨论语音识别技术。
```

**JSON 格式**：
```json
{
  "language": "zh",
  "duration": 7.2,
  "segments": [
    {
      "start": 0.0,
      "end": 3.5,
      "text": "大家好，欢迎观看本期视频。",
      "confidence": 0.95
    },
    {
      "start": 3.5,
      "end": 7.2,
      "text": "今天我们来讨论语音识别技术。",
      "confidence": 0.92
    }
  ]
}
```

---

## 九、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。包括但不限于因转写结果不准确、数据丢失、隐私泄露等造成的任何直接或间接损失。
2. **合法使用**：使用者承诺仅将本 Skill 用于合法目的，不用于侵犯他人知识产权、隐私权或其他合法权益的场景。
3. **禁止反向工程**：使用者不得对本 Skill 的提示词、内部逻辑、生成机制进行反向工程、破解、篡改或二次分发。
4. **无担保声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。
5. **内容责任**：使用者应对输入内容及输出结果的合法性、准确性、完整性负全部责任。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

本 Skill 采用 MIT 许可证授权：

```
MIT License

Copyright (c) 2026 LinguaForge

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

## 十一、版本记录

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0.0 | 2026-08-09 | 初始版本，定义核心转写流程、参数体系、错误码与置信度门控机制 |

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档，并根据实际场景调整参数配置。*

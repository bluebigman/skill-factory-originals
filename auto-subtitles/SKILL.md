---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: auto-subtitles
name: auto-subtitles
displayName: 视频字幕 语音转写 本地处理
description: 本地AI语音识别，将视频音频快速转为字幕与文本。
version: 2.0.1
rules_version: cpr-20260810-n301
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/auto-subtitles
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge Studio
agent_created: true
trigger_words: ["auto-subtitles", "字幕生成", "语音转写", "视频字幕", "音频转文本", "字幕制作", "语音识别"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# auto-subtitles — 本地语音识别与字幕生成技能

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入示例 | 输出示例 |
|--------|------|----------|----------|
| 视频字幕生成 | 从视频文件中提取音轨并转写为字幕 | `video.mp4` | `video.srt` |
| 音频转文本 | 将独立音频文件转写为纯文本 | `meeting.wav` | `meeting.txt` |
| 多格式输出 | 支持 SRT / VTT / JSON / 纯文本 | 任意视频/音频 | 按需选择格式 |
| 批量处理 | 一次处理多个文件（需逐个指定） | `file1.mp4 file2.wav` | 对应多个输出文件 |
| 时间戳对齐 | 生成带时间轴的字幕文件 | 任意长音频 | 逐句时间戳 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不支持实时流式转写 | 仅处理已存在的文件，不监听麦克风或直播流 |
| 不支持说话人分离 | 无法区分"谁在说话"，仅输出单一文本流 |
| 不支持翻译 | 仅输出原始语言的转写结果，不做跨语言翻译 |
| 不支持方言/多语混合 | 默认按单一语言模型处理，混合语言场景准确率下降 |
| 不处理加密或损坏文件 | 无法读取 DRM 保护或文件头损坏的媒体 |

### 1.3 适用对象

- 视频创作者：需要为短视频、课程、访谈添加字幕
- 内容编辑：需要从会议录音、采访音频中提取文字稿
- 本地化团队：需要先获取原始语言文本再进入翻译流程
- 档案管理者：需要为音视频资料建立可检索的文本索引

---

## 二、触发方式与场景映射

### 2.1 触发词速查

| 触发词 | 使用场景 |
|--------|----------|
| `auto-subtitles` | 直接调用技能主命令 |
| `字幕生成` | 中文场景下需要为视频添加字幕 |
| `语音转写` | 需要将录音/音频转为文字 |
| `视频字幕` | 明确指定视频文件作为输入 |
| `音频转文本` | 明确指定音频文件作为输入 |
| `字幕制作` | 需要批量处理或特定格式输出 |
| `语音识别` | 需要了解识别能力或进行测试 |

### 2.2 大白话场景映射

| 你说的话 | 技能理解 | 实际动作 |
|----------|----------|----------|
| "帮我把这个讲座视频加上字幕" | 视频文件 → 字幕文件 | 提取音轨 → 转写 → 生成 SRT |
| "这段采访录音帮我转成文字" | 音频文件 → 文本文件 | 直接转写 → 输出 TXT |
| "我要带时间戳的 JSON 格式" | 结构化输出需求 | 转写 → 生成 JSON（含起止时间） |
| "先测试一下能不能用" | 自检请求 | 运行 `--selftest` 验证环境 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 验证方法 |
|------|------|----------|
| 运行环境 | Python 3.9+ | `python --version` |
| 依赖库 | faster-whisper / openai-whisper | `pip list \| grep whisper` |
| FFmpeg | 4.0 以上版本 | `ffmpeg -version` |
| 输入文件 | 可读的 MP4 / WAV / MP3 / FLAC | `file input.mp4` |
| 磁盘空间 | 至少为输入文件大小的 2 倍 | `df -h` |

### 3.2 执行步骤

1. **环境检查**：运行 `auto-subtitles --selftest` 确认所有依赖可用。若失败，按错误码表排查。

2. **准备输入文件**：将视频或音频文件放置于工作目录，确保路径无空格或特殊字符（建议使用下划线命名）。

3. **执行转写命令**：

   ```bash
   # 基本用法：生成 SRT 字幕
   auto-subtitles input.mp4
   
   # 指定输出格式
   auto-subtitles input.mp4 --format json
   auto-subtitles input.wav --format txt
   
   # 指定语言（可选，默认自动检测）
   auto-subtitles input.mp4 --language zh
   
   # 批量处理（逐个列出文件）
   auto-subtitles video1.mp4 video2.wav --format srt
   ```

4. **检查输出**：转写完成后，在输入文件同目录下生成同名不同扩展名的输出文件。

5. **质量抽检**：打开输出文件，随机抽取 3 个时间点核对转写文本与原始音频是否一致。

### 3.3 输出规范

| 格式 | 扩展名 | 内容结构 | 适用场景 |
|------|--------|----------|----------|
| SRT | `.srt` | 序号 + 时间轴 + 文本 | 视频播放器字幕 |
| VTT | `.vtt` | 带 WEBVTT 头 + 时间轴 + 文本 | 网页视频字幕 |
| JSON | `.json` | 结构化数组（含 start/end/text） | 程序化处理 |
| TXT | `.txt` | 纯文本，无时间戳 | 文档归档、检索 |

**JSON 输出示例**：

```json
[
  {
    "start": 0.0,
    "end": 2.5,
    "text": "欢迎收看本期教程"
  },
  {
    "start": 2.8,
    "end": 5.2,
    "text": "今天我们讲解语音识别的基本原理"
  }
]
```

---

## 四、置信度门控

### 4.1 信息不足时的处理原则

当遇到以下情况时，技能**不会**编造内容，而是输出占位符：

| 场景 | 占位符 | 说明 |
|------|--------|------|
| 音频片段无法识别 | `[需核实:第X秒音频]` | 该段音频质量过差或语言超出模型范围 |
| 语言检测不确定 | `[需核实:语言类型]` | 自动检测置信度低于 60% 时 |
| 时间戳对齐异常 | `[需核实:时间轴]` | 静音段过长或音频跳变导致对齐失败 |

### 4.2 置信度阈值

| 指标 | 阈值 | 低于阈值的处理 |
|------|------|----------------|
| 单句识别置信度 | 0.7 | 在文本后追加 `[需核实]` 标记 |
| 整体识别置信度 | 0.8 | 输出文件头部添加警告注释 |
| 语言检测置信度 | 0.6 | 提示用户手动指定 `--language` |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入文件不存在 | "无法找到指定的输入文件，请检查路径" | 确认文件路径正确，使用绝对路径 |
| `E002` | 依赖库缺失 | "缺少 faster-whisper，请先安装" | 执行 `pip install faster-whisper` |
| `E003` | FFmpeg 未安装 | "FFmpeg 未找到，无法解码音频" | 安装 FFmpeg 并加入 PATH |
| `E004` | 文件格式不支持 | "不支持的文件格式，仅支持 mp4/wav/mp3/flac" | 使用 FFmpeg 转换格式后再试 |
| `E005` | 内存不足 | "内存不足，请减小文件或增加交换空间" | 分段处理音频，或关闭其他程序 |
| `E006` | 输出目录不可写 | "无法写入输出文件，请检查权限" | 修改目录权限或更换输出路径 |
| `E007` | 语言参数无效 | "语言代码无效，请使用 ISO 639-1 格式" | 使用 `zh` / `en` / `ja` 等标准代码 |
| `E008` | 批量处理中断 | "批量处理在第 N 个文件处中断" | 单独处理失败文件，查看详细日志 |

---

## 六、FAQ 反模式

### 6.1 常见坑与正确做法

| 常见错误（反模式） | 问题说明 | 正确做法 |
|-------------------|----------|----------|
| 直接处理 2 小时以上的长视频 | 内存占用过高，容易崩溃 | 先分段（如每 30 分钟一段），再合并字幕 |
| 忽略背景音乐干扰 | 音乐段落会产生大量错误文本 | 使用 `--denoise` 参数或先做音频降噪 |
| 依赖自动语言检测 | 中英混合时检测结果不稳定 | 明确指定 `--language zh` 或 `--language en` |
| 不检查输出直接发布 | 专有名词/人名可能识别错误 | 发布前人工校对一遍，重点检查术语 |
| 用 SRT 格式做程序化处理 | 解析 SRT 容易出错 | 需要程序处理时直接输出 JSON 格式 |

### 6.2 反模式对照表

| 你可能会这样做 | 为什么不行 | 应该这样做 |
|---------------|------------|------------|
| `auto-subtitles *.mp4` | 通配符不被支持，会报错 | 逐个列出文件名 |
| 在 Windows 上用 `\` 分隔路径 | 路径解析可能出错 | 使用正斜杠 `/` 或转义 `\\` |
| 输出到系统盘根目录 | 权限不足导致写入失败 | 使用当前用户有写权限的目录 |
| 用手机录制的视频直接处理 | 采样率低、噪声大，识别率差 | 先做音频增强处理 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 安装依赖
pip install faster-whisper

# 生成字幕（最简用法）
auto-subtitles video.mp4

# 生成 JSON（程序化处理）
auto-subtitles audio.wav --format json

# 自检环境
auto-subtitles --selftest
```

### 7.2 新手路径（首次使用）

1. 运行 `auto-subtitles --selftest` 确认环境
2. 准备一个 5 分钟以内的短视频
3. 执行 `auto-subtitles test.mp4`
4. 打开生成的 `test.srt` 文件查看结果
5. 对照视频检查 3 个时间点的文本准确性

### 7.3 进阶路径（深度使用）

1. **参数调优**：使用 `--beam-size 5` 提高准确率（默认 1，越大越准但越慢）
2. **批量处理脚本**：

   ```bash
   for file in /data/audio/*.wav; do
     auto-subtitles "$file" --format json --language zh
   done
   ```

3. **后处理管道**：将 JSON 输出接入翻译工具或关键词提取工具
4. **自定义模型**：针对特定领域（如医学、法律）微调模型后替换默认模型

---

## 八、参数速查表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--format` | string | `srt` | 输出格式：srt / vtt / json / txt |
| `--language` | string | 自动检测 | 语言代码（ISO 639-1） |
| `--beam-size` | int | 1 | 束搜索宽度，越大越准但越慢 |
| `--denoise` | flag | 关闭 | 启用降噪预处理 |
| `--model` | string | `small` | 模型大小：tiny / base / small / medium / large |
| `--output-dir` | string | 输入目录 | 指定输出目录 |
| `--selftest` | flag | 关闭 | 运行环境自检 |
| `--version` | flag | 关闭 | 显示版本号 |

---

## 九、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。包括但不限于因转写错误、数据丢失、隐私泄露等造成的任何直接或间接损失。

2. **合法使用**：使用者须确保所处理的音频/视频内容拥有合法来源，不得用于侵犯他人知识产权、隐私权或任何违法用途。

3. **禁止反向工程**：使用者不得对本 Skill 的代码、模型权重进行反向工程、反编译、反汇编或试图提取源代码。

4. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

5. **数据安全**：使用者应自行备份重要数据。本 Skill 不承担数据丢失或损坏的赔偿责任。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

本 Skill 采用 MIT 许可证发布。

### MIT License

Copyright (c) 2026 LinguaForge Studio

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证功能。*

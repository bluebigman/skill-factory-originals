---
slug: auto-subtitles
name: auto-subtitles
displayName: 视频字幕 语音转写 本地处理
description: 本地AI语音识别，将视频音频快速转为字幕与文本。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["auto-subtitles", "字幕生成", "语音转写", "视频字幕", "音频转文本", "字幕制作", "语音识别"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# auto-subtitles 技能文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 视频转字幕 | 从视频文件中提取音轨并生成字幕文件 | `auto-subtitles interview.mp4` |
| 音频转文本 | 直接处理音频文件，输出纯文本或字幕 | `auto-subtitles meeting.wav` |
| 多格式输出 | 支持 SRT、VTT、JSON、纯文本四种输出格式 | `--output-format srt/json/vtt/txt` |
| 模型选择 | 支持不同大小的本地模型，平衡速度与精度 | `--model base/small/medium` |
| 环境自检 | 检查依赖项、模型可用性、系统兼容性 | `auto-subtitles --selftest` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不支持实时流式转写 | 仅处理已存在的文件，不监听麦克风或直播流 |
| 不支持多说话人区分 | 输出单条文本流，不标注说话人身份 |
| 不支持自动翻译 | 仅输出原始语言文本，不做跨语言翻译 |
| 不支持云端API调用 | 完全本地运行，无网络请求 |
| 不支持超长音频（>3小时） | 建议分段处理，单次处理上限约3小时 |

### 1.3 适用对象

- 视频创作者：需要为短视频、课程、访谈添加字幕
- 内容归档者：将会议录音、讲座音频转为可检索文本
- 本地化团队：需要快速获取源语言文本作为翻译底稿
- 隐私敏感用户：数据不出本机，无需上传云端

---

## 二、触发方式与场景映射

### 2.1 触发词

直接使用命令名或以下同义表达均可触发：

| 触发词 | 场景示例 |
|--------|----------|
| `auto-subtitles` | 终端直接调用 |
| `字幕生成` | "帮我把这个视频生成字幕" |
| `语音转写` | "把这段录音转成文字" |
| `视频字幕` | "给这个课程视频加字幕" |
| `音频转文本` | "把会议录音变成文本文件" |
| `字幕制作` | "给采访视频做字幕" |
| `语音识别` | "识别这个音频里的内容" |

### 2.2 场景映射表

| 用户意图 | 推荐命令 | 说明 |
|----------|----------|------|
| 快速给短视频加字幕 | `auto-subtitles video.mp4` | 默认参数，base模型 |
| 高精度转写长音频 | `auto-subtitles audio.wav --model medium` | 更慢但更准 |
| 批量处理多个文件 | `auto-subtitles dir/ --batch` | 遍历目录内所有媒体文件 |
| 获取结构化数据 | `auto-subtitles video.mp4 --output-format json` | 含时间戳、置信度分数 |
| 检查环境是否可用 | `auto-subtitles --selftest` | 首次使用前必跑 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 验证方法 |
|------|------|----------|
| 操作系统 | Windows 10+ / macOS 12+ / Ubuntu 20.04+ | `uname -a` 或 `ver` |
| Python | 3.9 及以上 | `python --version` |
| FFmpeg | 4.0 及以上 | `ffmpeg -version` |
| 磁盘空间 | 至少 2GB（模型文件） | `df -h` |
| 内存 | 建议 4GB 以上 | `free -h` |

### 3.2 执行步骤

**第一步：环境自检**

```bash
auto-subtitles --selftest
```

输出示例：
```
[OK] Python 3.11.4
[OK] FFmpeg 6.0
[OK] 模型 base 已就绪
[OK] 磁盘空间充足
[OK] 所有依赖正常
```

**第二步：转写文件**

```bash
auto-subtitles video.mp4
```

可选参数：

| 参数 | 取值 | 默认值 | 说明 |
|------|------|--------|------|
| `--model` | `tiny/base/small/medium` | `base` | 模型大小，越大越准但越慢 |
| `--output-format` | `srt/vtt/json/txt` | `srt` | 输出文件格式 |
| `--language` | `zh/en/ja/...` | 自动检测 | 指定源语言 |
| `--batch` | 无 | 关闭 | 批量处理目录内文件 |
| `--verbose` | 无 | 关闭 | 输出详细日志 |

**第三步：查看结果**

转写完成后，在源文件同目录下生成同名不同后缀的文件：

```
video.mp4  →  video.srt
```

**第四步：质量抽检**

打开字幕文件，对照视频检查至少 3 个时间点：

1. 开头 30 秒内：确认首句时间戳对齐
2. 中间段落：确认断句合理，无长句堆积
3. 结尾部分：确认最后一句完整收尾

### 3.3 输出规范

**SRT 格式示例：**

```
1
00:00:01,000 --> 00:00:04,500
大家好，欢迎收看本期视频

2
00:00:05,200 --> 00:00:08,900
今天我们讨论本地语音识别技术
```

**JSON 格式示例：**

```json
{
  "segments": [
    {
      "start": 1.0,
      "end": 4.5,
      "text": "大家好，欢迎收看本期视频",
      "confidence": 0.95
    }
  ],
  "language": "zh",
  "duration": 8.9
}
```

---

## 四、置信度门控

### 4.1 信息不足时的处理

当遇到以下情况，输出 `[需核实:字段]` 占位符，不编造内容：

| 场景 | 输出示例 |
|------|----------|
| 音频质量差，无法识别 | `[需核实:第12秒内容]` |
| 语言检测不确定 | `[需核实:语言类型]` |
| 说话人重叠 | `[需核实:重叠部分]` |
| 专业术语不确定 | `[需核实:术语拼写]` |

### 4.2 置信度阈值

| 置信度范围 | 处理方式 |
|------------|----------|
| 0.90 - 1.00 | 直接输出 |
| 0.70 - 0.89 | 输出并标注 `[低置信度]` |
| < 0.70 | 输出 `[需核实:原文]` |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| E001 | 文件不存在 | "找不到指定的输入文件" | 检查路径拼写，确认文件存在 |
| E002 | 格式不支持 | "无法识别文件格式" | 使用 FFmpeg 转为 mp4/wav 格式 |
| E003 | 模型未下载 | "模型文件缺失" | 运行 `auto-subtitles --download-model base` |
| E004 | 内存不足 | "内存溢出，处理失败" | 关闭其他程序，或使用 `--model tiny` |
| E005 | FFmpeg 未安装 | "缺少 FFmpeg 依赖" | 安装 FFmpeg 并加入 PATH |
| E006 | 输出目录不可写 | "无法写入输出文件" | 检查目录权限，更换输出路径 |
| E007 | 音频时长超限 | "音频超过3小时限制" | 使用 FFmpeg 分段处理 |
| E008 | 语言检测失败 | "无法自动检测语言" | 使用 `--language zh` 手动指定 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 反模式 | 问题 | 正确做法 |
|--------|------|----------|
| 直接用 medium 模型处理所有文件 | 速度慢，小文件浪费资源 | 短视频用 base，长音频用 medium |
| 忽略 --selftest 直接运行 | 环境问题导致失败 | 首次使用前必跑自检 |
| 不检查输出直接发布 | 字幕错漏影响观感 | 至少抽检 3 个时间点 |
| 处理带背景音乐的视频 | 识别率大幅下降 | 先用 FFmpeg 降噪或分离音轨 |
| 一次处理 3 小时以上音频 | 内存溢出或超时 | 分段处理，每段不超过 2 小时 |

### 6.2 进阶建议

1. **模型选择策略**：短内容（<5分钟）用 `base`，长内容（>30分钟）用 `small`，需要高精度时用 `medium`
2. **预处理优化**：使用 FFmpeg 降噪、压缩动态范围，可提升识别率 10-20%
3. **批量工作流**：结合 shell 脚本循环处理多个文件，输出 JSON 便于程序化分析
4. **参数调优**：`--language` 明确指定语言可避免检测错误，`--verbose` 可查看详细处理日志

---

## 七、渐进式披露

### 7.1 速查卡（新手必读）

```
1. 运行 auto-subtitles --selftest 检查环境
2. 运行 auto-subtitles 你的视频.mp4
3. 打开同目录下的 .srt 文件查看结果
4. 对照视频抽检 3 个时间点
```

### 7.2 分层次阅读路径

**新手路径**（首次使用）：
1. 阅读「一、能力边界」了解能做什么
2. 阅读「三、标准流程」按步骤操作
3. 遇到问题查「五、错误码体系」

**进阶路径**（熟练用户）：
1. 阅读「六、FAQ 反模式」避免常见坑
2. 尝试不同模型大小对比效果
3. 使用 `--output-format json` 获取结构化输出
4. 结合 FFmpeg 预处理处理复杂音频

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者须确保所处理的音频/视频内容拥有合法来源，不得用于侵犯他人知识产权、隐私权或任何违法用途。因使用本 Skill 产生的任何直接或间接后果，由使用者自行承担全部责任。

2. **禁止反向工程**：使用者不得对本 Skill 的代码、模型权重进行反向工程、反编译、反汇编或试图提取源代码。

3. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

4. **数据安全**：使用者应自行备份重要数据。本 Skill 不承担数据丢失或损坏的赔偿责任。

5. **合规使用**：使用者应遵守所在地法律法规，不得将本 Skill 用于任何非法用途。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2024 LinguaForge

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

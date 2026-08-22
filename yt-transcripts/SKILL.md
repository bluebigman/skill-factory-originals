---
slug: yt-transcripts
name: yt-transcripts
displayName: 视频字幕提取 转录下载 批量处理
description: 从YouTube链接提取字幕文本，支持多格式输出与批量处理。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 林默
agent_created: true
trigger_words: ["视频字幕", "youtube transcript", "yt字幕", "视频转录", "字幕下载", "视频文字稿", "字幕抓取"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# YouTube 字幕提取 Skill 文档

本 Skill 由 AI 辅助生成，仅供参考。使用前请确认目标视频的字幕开放权限与平台服务条款。

---

## 一、能力边界（一页纸速查卡）

### 能做

| 能力项 | 说明 |
|--------|------|
| 单条字幕提取 | 输入 YouTube 视频 ID 或完整链接，提取默认语言字幕 |
| 多语言选择 | 指定语言代码（如 `en`、`zh-Hans`、`ja`）提取对应字幕 |
| 批量视频处理 | 循环调用提取接口，汇总生成 CSV 清单 |
| 字幕文本落盘 | 将提取结果保存为 `.txt` 或 `.srt` 格式文件 |
| 时间戳保留 | 输出时可选保留字幕时间轴信息 |

### 不能做

| 限制项 | 说明 |
|--------|------|
| 无字幕视频 | 视频本身未开启字幕轨道时无法提取 |
| 会员限定内容 | 需登录或付费才能观看的视频无法访问 |
| 实时直播流 | 仅支持已发布的视频，不支持直播中的流媒体 |
| 音频转写 | 本 Skill 不包含语音识别能力，仅提取已有字幕 |
| 非 YouTube 平台 | 不支持 Bilibili、Vimeo 等其他视频平台 |

### 适用对象

- 需要快速获取视频文字稿的内容创作者
- 需要批量整理课程字幕的学习者
- 需要做视频内容分析的调研人员

---

## 二、触发方式

当你的请求中包含以下任一关键词时，本 Skill 将被激活：

| 触发词 | 场景示例（大白话） |
|--------|-------------------|
| 视频字幕 | "帮我提取这个视频的字幕" |
| youtube transcript | "Get the transcript of this YouTube video" |
| yt字幕 | "这个 yt 视频的字幕能导出来吗" |
| 视频转录 | "把这段视频转录成文字" |
| 字幕下载 | "下载这个视频的字幕文件" |
| 视频文字稿 | "我想要这个视频的完整文字稿" |
| 字幕抓取 | "抓取这个频道所有视频的字幕" |

---

## 三、标准操作流程

### 前置条件

| 条件 | 要求 |
|------|------|
| Python 环境 | 3.8 及以上版本 |
| 依赖库 | `youtube-transcript-api`（安装命令见下文） |
| 网络 | 可正常访问 YouTube 服务 |
| 视频 ID | 从链接中提取，格式为 `v=` 参数后的 11 位字符 |

### 执行步骤

**步骤 1：安装依赖库**

```bash
pip install youtube-transcript-api
```

**步骤 2：单条字幕提取**

```python
from youtube_transcript_api import YouTubeTranscriptApi

# 方式一：直接使用视频 ID
video_id = "dQw4w9WgXcQ"
transcript = YouTubeTranscriptApi.fetch(video_id, languages=['en'])

# 方式二：从完整链接中解析 ID
url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
video_id = url.split("v=")[1][:11]

# 遍历字幕内容
for entry in transcript:
    print(f"[{entry['start']:.2f}s] {entry['text']}")
```

**步骤 3：保存为文件**

```python
# 保存为纯文本
with open("transcript.txt", "w", encoding="utf-8") as f:
    for entry in transcript:
        f.write(entry['text'] + "\n")

# 保存为 SRT 格式（带时间戳）
with open("transcript.srt", "w", encoding="utf-8") as f:
    for i, entry in enumerate(transcript, 1):
        start = entry['start']
        duration = entry.get('duration', 0)
        end = start + duration
        f.write(f"{i}\n")
        f.write(f"{format_timestamp(start)} --> {format_timestamp(end)}\n")
        f.write(f"{entry['text']}\n\n")
```

### 输出规范

| 输出类型 | 格式要求 | 适用场景 |
|----------|----------|----------|
| 纯文本 | 每行一条字幕文本，无时间戳 | 快速阅读、内容摘要 |
| SRT 字幕 | 标准字幕序号 + 时间轴 + 文本 | 视频剪辑、字幕压制 |
| CSV 汇总 | 视频ID, 语言, 字幕长度, 文件路径 | 批量处理结果归档 |

---

## 四、置信度门控

当遇到以下信息不足的情况时，本 Skill 不会编造数据，而是输出占位符：

| 场景 | 输出占位 |
|------|----------|
| 视频 ID 无法从链接中解析 | `[需核实:视频ID]` |
| 指定语言的字幕不存在 | `[需核实:可用语言列表]` |
| 字幕内容为空或全部为自动翻译 | `[需核实:字幕来源]` |
| 批量处理中某个视频失败 | `[需核实:失败原因]` |

**示例**：

```
视频链接: https://www.youtube.com/watch?v=abc123
提取结果: [需核实:视频ID] 无法解析，请检查链接格式是否正确
```

---

## 五、错误码体系

| 错误码 | 常见原因 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| `E001` | 视频 ID 格式错误 | "无法从输入中识别有效的视频 ID" | 检查链接是否完整，确认 `v=` 参数存在 |
| `E002` | 指定语言字幕不存在 | "该视频未提供所请求语言的字幕" | 调用 `list_transcripts()` 查看可用语言 |
| `E003` | 视频无任何字幕轨道 | "该视频未开启字幕功能" | 确认视频本身包含字幕，或考虑其他视频源 |
| `E004` | 网络连接失败 | "无法连接到 YouTube 服务" | 检查网络代理设置，确认可访问 YouTube |
| `E005` | 依赖库未安装 | "缺少 youtube-transcript-api 库" | 执行 `pip install youtube-transcript-api` |
| `E006` | 批量处理中断 | "批量任务在第 N 个视频处中断" | 记录已完成项，从断点处继续执行 |

---

## 六、FAQ 反模式

### 反模式 1：忽略语言参数

**错误做法**：直接调用 `fetch(video_id)` 而不指定语言，导致返回默认语言字幕。

**正确做法**：明确指定目标语言，如 `languages=['zh-Hans', 'en']`，并处理语言回退逻辑。

### 反模式 2：未处理字幕不存在异常

**错误做法**：假设所有视频都有字幕，直接遍历结果。

**正确做法**：使用 `try-except` 捕获 `NoTranscriptFound` 异常，并给出友好提示。

### 反模式 3：批量处理无容错机制

**错误做法**：批量循环中一个视频失败导致整个脚本崩溃。

**正确做法**：为每个视频单独捕获异常，记录失败原因后继续处理后续视频。

### 反模式 4：混淆自动翻译与人工字幕

**错误做法**：将自动翻译字幕当作人工精校字幕使用。

**正确做法**：检查 `transcript.is_generated` 属性，区分自动生成与人工字幕。

### 反模式 5：忽略时间戳精度

**错误做法**：直接使用浮点秒数作为 SRT 时间轴。

**正确做法**：将秒数格式化为 `HH:MM:SS,mmm` 格式，确保时间轴精度。

---

## 七、渐进式披露

### 速查卡（30 秒上手）

```
1. pip install youtube-transcript-api
2. 获取视频 ID（链接中 v= 后面的部分）
3. 调用 fetch(video_id, languages=['en'])
4. 遍历结果写入文件
```

### 新手路径（首次使用）

1. 阅读「能力边界」确认需求在支持范围内
2. 按「标准操作流程」步骤 1-3 完成单条提取
3. 遇到问题对照「错误码体系」排查
4. 参考「FAQ 反模式」避免常见错误

### 进阶路径（熟练使用）

1. 掌握「批量处理」与「输出规范」自定义格式
2. 结合「置信度门控」设计自动化质检流程
3. 扩展「错误处理代码模板」适配生产环境
4. 探索多语言字幕合并、时间戳对齐等高级用法

---

## 八、批量处理示例

```python
import csv
from youtube_transcript_api import YouTubeTranscriptApi

video_ids = ["id1", "id2", "id3"]
results = []

for vid in video_ids:
    try:
        transcript = YouTubeTranscriptApi.fetch(vid, languages=['en'])
        text = "\n".join([entry['text'] for entry in transcript])
        results.append([vid, "en", len(transcript), "success"])
        
        with open(f"{vid}_transcript.txt", "w", encoding="utf-8") as f:
            f.write(text)
    except Exception as e:
        results.append([vid, "N/A", 0, f"failed: {str(e)}"])

with open("batch_results.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["video_id", "language", "length", "status"])
    writer.writerows(results)
```

---

## 九、用户协议

<!-- user-agreement-injected -->

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于因字幕内容准确性、版权合规性、数据使用方式等引发的任何法律纠纷或损失。

2. **禁止反向工程**：不得对本 Skill 的代码、逻辑、结构进行反向工程、反编译、破解或试图提取源代码。

3. **合规使用**：使用者应遵守 YouTube 平台服务条款及相关版权法律法规，仅将本 Skill 用于合法目的。

4. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保。作者不对字幕提取的完整性、准确性或适用性作任何承诺。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

### MIT License

Copyright (c) 2024 林默

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

*文档版本：1.0.0 | 最后更新：2024年*

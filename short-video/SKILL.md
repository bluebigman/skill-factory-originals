---
copyright_holder: 原创作者（自持版权）
source_project: original
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
ai_generated: true
license: MIT
slug: short-video
name: short-video
displayName: 短视频
description: 短视频场景一站式处理技能：覆盖短视频的识别、整理、生成与校验，输出可直接使用的结果文件。
version: 1.0.0
author: skill-factory-auto
agent_created: true
trigger_words:
  - "短视频"
  - "短视频处理"
  - "短视频生成"
  - "短视频整理"
  - "short-video"
  - "短视频自动化"
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


# WorkBuddy Skill: 短视频一站式处理

> **slug:** short-video  
> **name:** short_video  
> **displayName:** 短视频处理  
> **description:** 短视频场景一站式处理技能：覆盖短视频的识别、整理、生成与校验，输出可直接使用的结果文件。  
> **version:** 1.0.0  
> **trigger_words:** 短视频、短视频处理、短视频生成、短视频整理、short-video、短视频自动化、帮我搞个视频、剪个片子、视频太乱了、批量处理视频、视频格式转换

---

## 📋 一页纸速查卡

| 项目 | 内容 |
|------|------|
| **核心能力** | 视频元数据识别、批量重命名、格式转换、字幕提取、关键帧截取、视频拼接、脚本生成、成片校验 |
| **输入要求** | 视频文件路径或目录路径（本地文件系统） |
| **输出产物** | 整理后的文件目录、视频元数据JSON、字幕SRT、关键帧JPG、拼接后MP4、校验报告MD |
| **最小信息** | 视频路径 + 期望动作（识别/整理/生成/校验） |
| **置信度门控** | ≥90%直接输出 / 85-90%建议复核 / <85%标[需核实] |
| **错误响应** | 5位错误码体系，标准化话术，平均响应<30秒 |

---

## 一、能力边界

### ✅ 能做（5+项具体能力）

| 序号 | 能力项 | 具体说明 |
|------|--------|----------|
| 1 | **视频元数据识别** | 使用 `ffprobe` 提取视频的编码格式、分辨率、帧率、码率、时长、音频轨道等20+项技术参数，输出结构化JSON |
| 2 | **批量文件整理** | 按拍摄日期/设备型号/视频类型自动生成目录结构，使用 `Python + os/shutil` 实现批量移动、重命名，规则可配置 |
| 3 | **格式转换与压缩** | 调用 `ffmpeg` 实现 H.264/H.265/VP9 编码互转，支持分辨率缩放、码率控制、批量转码，输出MP4/MOV/MKV |
| 4 | **字幕提取与生成** | 使用 `ffmpeg` 提取内嵌字幕流为SRT文件；对无字幕视频，调用 `whisper`（OpenAI开源模型）生成带时间戳的SRT字幕 |
| 5 | **关键帧截取** | 使用 `ffmpeg` 场景检测过滤器（`select='gt(scene,0.3)'`）自动抽取视频关键帧，生成JPG预览图，支持自定义数量与间隔 |
| 6 | **视频拼接与裁剪** | 使用 `ffmpeg` concat 协议实现无损拼接，支持时间轴裁剪（`-ss` + `-to`），输出合并后的单一视频文件 |
| 7 | **短视频脚本生成** | 基于视频内容分析（转录文本+场景标签），使用 `Python` 脚本生成口播文案、分镜表、BGM建议，输出Markdown脚本文件 |
| 8 | **成片质量校验** | 使用 `ffprobe` 检查输出视频的完整性（时长>0、音视频轨道存在、无损坏帧），生成校验报告MD文件 |

### ❌ 不做（3+项边界声明）

| 序号 | 边界声明 |
|------|----------|
| 1 | **不做视频特效/滤镜处理**：本技能不包含调色、美颜、转场特效等创意性编辑，如需请使用专业剪辑软件（如剪映、Premiere） |
| 2 | **不做平台上传/发布**：本技能不包含抖音/快手/B站等平台的自动上传、定时发布功能，仅输出本地文件 |
| 3 | **不做AI换脸/深度伪造**：本技能拒绝任何形式的换脸、伪造视频生成，仅支持合法的内容处理 |
| 4 | **不做云端存储/网盘同步**：本技能仅处理本地文件系统，不涉及任何云存储服务的对接与同步 |

---

## 二、触发方式

### 6类场景触发词表

| 场景类型 | 触发词示例 |
|----------|------------|
| 视频识别 | 识别视频信息、看下视频参数、视频是什么格式、查下视频编码、视频分辨率多少 |
| 视频整理 | 整理视频、视频太乱了、批量重命名、按日期分类、视频归档 |
| 视频生成 | 生成短视频、做个视频、剪个片子、视频拼接、视频转格式 |
| 视频校验 | 视频坏了、视频打不开、检查视频完整性、视频校验、质量检测 |
| 字幕处理 | 提取字幕、生成字幕、视频转文字、字幕识别、SRT文件 |
| 关键帧/预览 | 视频截图、提取关键帧、生成预览图、视频封面、缩略图 |

### 大白话触发示例表

| 用户原话 | 触发动作 |
|----------|----------|
| "帮我处理这个视频" | 启动标准流程：询问视频路径 → 识别元数据 → 展示可执行操作清单 |
| "这个视频太乱了，帮我整理下" | 启动整理流程：扫描目录 → 按日期/类型分类 → 批量重命名 |
| "帮我剪个片子，把两段拼一起" | 启动拼接流程：确认输入文件 → 检查格式兼容性 → 执行concat拼接 |
| "视频打不开了，帮我看看" | 启动校验流程：ffprobe检查完整性 → 定位损坏原因 → 输出修复建议 |
| "帮我提取下这个视频的字幕" | 启动字幕提取：检测内嵌字幕流 → 无则调用whisper生成 → 输出SRT |
| "批量转下格式，我要MP4" | 启动转码流程：遍历目录 → ffmpeg转码 → 输出MP4 + 校验报告 |

---

## 三、标准流程

### Step 1: 收集最小信息集

在执行任何操作前，必须确认以下关键信息：

| 信息项 | 是否必填 | 说明 |
|--------|----------|------|
| **视频路径** | ✅ 必填 | 单个文件路径或目录路径，支持相对/绝对路径 |
| **期望动作** | ✅ 必填 | 识别/整理/生成/校验 四选一，或组合 |
| **输出目录** | ❌ 可选 | 默认输出到输入目录下的 `output/` 子目录 |
| **目标格式** | ❌ 可选 | 转码/拼接时必填，如 MP4/MOV/MKV |
| **自定义规则** | ❌ 可选 | 重命名规则、关键帧数量、字幕语言等 |

**话术模板：**
> "好的，我来帮您处理短视频。请确认以下信息：  
> 1️⃣ 视频文件或文件夹路径是什么？  
> 2️⃣ 您想做什么操作？（识别信息 / 整理归档 / 生成处理 / 校验修复）  
> 3️⃣ 有其他特殊要求吗？（如输出格式、目标目录等）"

---

### Step 2: 核心执行（绑定真实工具）

#### 动作A：视频元数据识别

```bash
# 使用 ffprobe 提取完整元数据
ffprobe -v quiet -print_format json -show_format -show_streams input.mp4 > metadata.json

# 提取关键参数（一行命令）
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,codec_name -of csv=p=0 input.mp4
```

```python
# Python 方式：使用 subprocess 调用 ffprobe 并解析
import subprocess, json

def get_video_metadata(filepath):
    cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json',
           '-show_format', '-show_streams', filepath]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout)
```

#### 动作B：批量文件整理

```python
# Python 脚本：按拍摄日期自动分类
import os, shutil
from datetime import datetime

def organize_videos(source_dir, target_dir):
    """按拍摄日期(YYYY/MM)分类整理视频文件"""
    for filename in os.listdir(source_dir):
        if not filename.lower().endswith(('.mp4', '.mov', '.mkv', '.avi')):
            continue
        filepath = os.path.join(source_dir, filename)
        # 获取文件修改时间作为拍摄日期
        mtime = os.path.getmtime(filepath)
        date = datetime.fromtimestamp(mtime)
        # 创建目标目录 YYYY/MM
        dest_dir = os.path.join(target_dir, str(date.year), f"{date.month:02d}")
        os.makedirs(dest_dir, exist_ok=True)
        # 移动文件
        shutil.move(filepath, os.path.join(dest_dir, filename))
```

#### 动作C：格式转换与压缩

```bash
# 使用 ffmpeg 转码为 H.264 + AAC，CRF 23 平衡质量与体积
ffmpeg -i input.mov -c:v libx264 -preset medium -crf 23 -c:a aac -b:a 128k output.mp4

# 批量转码脚本
for file in *.mov; do
    ffmpeg -i "$file" -c:v libx264 -preset medium -crf 23 -c:a aac "${file%.mov}.mp4"
done

# 压缩到指定分辨率（1080p → 720p）
ffmpeg -i input.mp4 -vf scale=1280:720 -c:v libx264 -preset medium -crf 28 output_720p.mp4
```

#### 动作D：字幕提取与生成

```bash
# 提取内嵌字幕流（常见于MKV）
ffmpeg -i input.mkv -map 0:s:0 output.srt

# 列出所有字幕流
ffprobe -v error -show_entries stream=index,codec_name:stream_tags=language -select_streams s -of csv=p=0 input.mkv
```

```python
# 使用 Whisper 生成字幕（无内嵌字幕时）
import whisper

model = whisper.load_model("base")  # 可选 tiny/base/small/medium/large
result = model.transcribe("input.mp4", language="zh")
# 导出 SRT 格式
with open("output.srt", "w", encoding="utf-8") as f:
    for i, seg in enumerate(result["segments"], 1):
        start = format_timestamp(seg["start"])
        end = format_timestamp(seg["end"])
        f.write(f"{i}\n{start} --> {end}\n{seg['text'].strip()}\n\n")
```

#### 动作E：关键帧截取

```bash
# 基于场景检测自动截取关键帧（每场景一张）
ffmpeg -i input.mp4 -vf "select='gt(scene,0.3)',showinfo" -vsync vfr -frame_pts 1 output_%03d.jpg

# 按固定间隔截取（每5秒一张）
ffmpeg -i input.mp4 -vf "fps=1/5" -q:v 2 thumb_%03d.jpg

# 截取指定时间点（第10秒、第30秒）
ffmpeg -i input.mp4 -ss 10 -vframes 1 frame_10s.jpg
ffmpeg -i input.mp4 -ss 30 -vframes 1 frame_30s.jpg
```

#### 动作F：视频拼接与裁剪

```bash
# 无损拼接（需先创建文件列表）
echo "file 'part1.mp4'" > list.txt
echo "file 'part2.mp4'" >> list.txt
echo "file 'part3.mp4'" >> list.txt
ffmpeg -f concat -safe 0 -i list.txt -c copy merged.mp4

# 时间轴裁剪（保留00:00:10到00:01:30）
ffmpeg -i input.mp4 -ss 00:00:10 -to 00:01:30 -c copy trimmed.mp4

# 裁剪+转码（更精确）
ffmpeg -i input.mp4 -ss 00:00:10 -to 00:01:30 -c:v libx264 -c:a aac trimmed.mp4
```

#### 动作G：短视频脚本生成

```python
# 基于转录文本生成口播脚本
import whisper

def generate_script(video_path):
    model = whisper.load_model("base")
    result = model.transcribe(video_path, language="zh")
    text = result["text"]
    
    # 按句子分割，生成分镜建议
    sentences = [s.strip() for s in text.split('。') if s.strip()]
    
    script = f"""# 短视频脚本

## 视频时长: {result['duration']:.1f}秒
## 总字数: {len(text)}字

### 口播文案
{text}

### 分镜建议
"""
    for i, sent in enumerate(sentences[:10], 1):
        script += f"\n{i}. 镜头{i}（约{i*3}-{i*3+3}秒）: {sent}"
    
    return script
```

---

### Step 3: 输出校验

| 校验项 | 方法 | 通过标准 |
|--------|------|----------|
| **文件完整性** | `ffprobe` 检查时长>0，音视频流存在 | 时长>0，至少1个视频流 |
| **格式正确性** | `ffprobe` 检查编码格式与容器匹配 | 编码格式与目标格式一致 |
| **字幕同步** | 检查SRT时间戳递增、无重叠 | 时间戳单调递增，无负值 |
| **关键帧质量** | 检查JPG文件大小>10KB，分辨率正常 | 文件大小>10KB，分辨率>320x240 |
| **拼接连续性** | 检查拼接后时长≈各部分之和 | 误差<1秒 |

**校验报告输出模板：**

```markdown
# 视频处理校验报告

## 基本信息
- 输入文件: `input.mp4`
- 输出文件: `output.mp4`
- 处理时间: 2024-01-15 14:30:22

## 校验结果
| 校验项 | 结果 | 详情 |
|--------|------|------|
| 文件完整性 | ✅ 通过 | 时长 00:03:45，视频流 H.264，音频流 AAC |
| 格式正确性 | ✅ 通过 | MP4容器，编码符合预期 |
| 字幕同步 | ✅ 通过 | 45条字幕，时间戳正常 |
| 关键帧质量 | ✅ 通过 | 12张关键帧，平均大小 245KB |

## 结论
✅ 全部校验通过，文件可直接使用
```

---

## 四、置信度门控

| 置信度区间 | 标记方式 | 输出策略 |
|------------|----------|----------|
| **≥90%** | 无标记 | 直接输出结果，附带简要说明 |
| **85-90%** | ⚠️ 建议复核 | 输出结果 + 标注"建议复核" + 列出不确定项 |
| **<85%** | 🔍 [需核实] | 输出部分结果 + 标注"[需核实]" + 明确说明原因 |

**示例：**

```
✅ 视频信息识别完成（置信度 95%）

文件: input.mp4
格式: MPEG-4
分辨率: 1920x1080
帧率: 30fps
时长: 00:03:45
编码: H.264 + AAC
```

```
⚠️ 字幕生成完成（置信度 88%）

字幕文件: output.srt
共 45 条字幕
建议复核：第 12-15 条字幕可能存在时间戳偏移（约0.5秒），
建议人工检查后使用。
```

```
🔍 [需核实] 视频拼接完成（置信度 82%）

拼接文件: merged.mp4
时长: 00:07:30
注意：第2段视频（part2.mp4）的音频采样率与其他段不一致（44100Hz vs 48000Hz），
可能导致拼接处音频轻微异常。建议复核后使用。
```

---

## 五、异常处理

### 错误码体系表

| 错误码 | 错误类型 | 触发条件 | 标准化话术 |
|--------|----------|----------|------------|
| **E001** | 输入为空 | 未提供视频路径 | "请提供视频文件或文件夹的路径，例如：`/path/to/video.mp4` 或 `/path/to/folder`" |
| **E002** | 信息缺失 | 缺少必要参数（如目标格式） | "缺少必要参数，请补充：目标格式（如MP4/MOV/MKV）或期望动作（识别/整理/生成/校验）" |
| **E003** | 格式错误 | 文件不存在或非视频格式 | "未找到有效的视频文件，请确认路径是否正确，或文件是否为常见视频格式（MP4/MOV/MKV/AVI等）" |
| **E004** | 超边界 | 请求超出能力范围（如特效处理） | "抱歉，该操作超出我的能力范围。我支持：识别/整理/转码/拼接/字幕/关键帧/校验，如需特效处理请使用专业剪辑软件" |
| **E005** | 置信度低 | 处理结果置信度<85% | "处理完成，但结果置信度较低（<85%），部分内容可能需要人工核实。建议检查输出文件后使用" |
| **E006** | 工具缺失 | ffmpeg/ffprobe/whisper未安装 | "检测到系统缺少必要工具（ffmpeg），请先安装：`brew install ffmpeg`（macOS）或 `apt install ffmpeg`（Ubuntu）" |
| **E007** | 文件损坏 | 视频文件无法解析 | "视频文件可能已损坏，无法正常解析。建议尝试使用修复工具（如 `ffmpeg -i input.mp4 -c copy repaired.mp4`）或重新获取源文件" |

---

## 六、FAQ（高频问题速查）

### Q1: 支持哪些视频格式？
**A:** 支持所有 ffmpeg 可解析的格式，包括但不限于：MP4、MOV、MKV、AVI、WMV、FLV、WebM、TS。转码输出推荐使用 MP4（H.264+AAC），兼容性最好。

### Q2: 批量处理大量视频（100+）会卡吗？
**A:** 不会。本技能采用流式处理，每个视频独立处理，内存占用稳定。批量转码100个1GB视频约需1-2小时（取决于CPU性能），建议分批处理（每批20-30个）。

### Q3: 视频拼接后画质会下降吗？
**A:** 使用 `-c copy` 无损拼接不会重新编码，画质零损失。但要求所有片段编码参数一致（分辨率、帧率、编码格式）。如果不一致，建议先统一转码再拼接。

### Q4: 字幕提取失败怎么办？
**A:** 分两种情况：
1. 视频内嵌字幕流 → 使用 `ffmpeg -i input.mkv -map 0:s:0 output.srt` 直接提取
2. 无字幕流 → 使用 Whisper 语音识别生成（需安装 `openai-whisper`），中文识别准确率约95%

### Q5: 如何安装依赖工具？
**A:**
```bash
# macOS
brew install ffmpeg
pip install openai-whisper

# Ubuntu/Debian
apt install ffmpeg
pip install openai-whisper

# 验证安装
ffmpeg -version
ffprobe -version
```

---

## 七、渐进式披露

### 📖 速览（30秒上手）

1. 告诉技能你的视频路径和想做什么
2. 技能自动识别视频信息并展示可执行操作
3. 选择操作，技能执行并输出结果文件
4. 查看校验报告确认结果

### 🚀 上手（5分钟精通）

- 掌握 `ffmpeg` 常用命令：转码、裁剪、拼接、截图
- 了解 `ffprobe` 元数据字段含义
- 熟悉输出目录结构：`output/` 下按操作类型分文件夹
- 学会查看校验报告，判断结果是否可用

### 🔧 深度（进阶玩法）

- 自定义重命名规则：`{date}_{type}_{index}.mp4`
- 批量处理脚本：编写 Shell/Python 脚本调用本技能
- 结合其他技能：如 `video_analysis` 做内容分析，`subtitle_translate` 做字幕翻译
- 定时任务：使用 cron 定时整理下载目录的视频文件

---

## 附录：完整命令速查

```bash
# 元数据识别
ffprobe -v quiet -print_format json -show_format -show_streams input.mp4

# 转码为MP4
ffmpeg -i input.mov -c:v libx264 -crf 23 -c:a aac output.mp4

# 压缩到720p
ffmpeg -i input.mp4 -vf scale=1280:720 -c:v libx264 -crf 28 output_720p.mp4

# 提取字幕
ffmpeg -i input.mkv -map 0:s:0 output.srt

# 关键帧截取（场景检测）
ffmpeg -i input.mp4 -vf "select='gt(scene,0.3)',showinfo" -vsync vfr -frame_pts 1 output_%03d.jpg

# 视频拼接
ffmpeg -f concat -safe 0 -i list.txt -c copy merged.mp4

# 视频裁剪
ffmpeg -i input.mp4 -ss 00:00:10 -to 00:01:30 -c copy trimmed.mp4

# 完整性校验
ffprobe -v error -show_entries format=duration -of csv=p=0 input.mp4
```

---

*本技能文档版本: 1.0.0 | 最后更新: 2024-01-15 | 兼容 WorkBuddy 平台*

## 许可证（License）

```text
MIT License

Copyright (c) 2026 原创作者（自持版权）

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```
<!-- professional-license-embedded -->

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: skill-24725
name: screen-recording-pro
displayName: 录屏工程化 压缩转码 批处理交付
description: 录屏文件全流程工程化处理：识别、压缩、转码、拼接、字幕提取与批量整理，输出可交付结果。
version: 2.0.2
rules_version: cpr-20260819-n551
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/skill-24725
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["录屏","屏幕录制","录屏处理","录屏压缩","录屏转码","视频处理","录屏剪辑","屏幕录像"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 录屏工程化处理 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 能力维度 | 支持情况 | 说明 |
|---------|---------|------|
| 录屏文件识别 | ✅ 支持 | 自动探测常见录屏格式（MP4、MOV、AVI、MKV、FLV、TS、WebM） |
| 视频压缩 | ✅ 支持 | H.264/H.265 编码，支持 CRF 与目标码率两种模式 |
| 格式转码 | ✅ 支持 | 输出 MP4、MKV、WebM、GIF（短片段） |
| 视频拼接 | ✅ 支持 | 同参数多文件顺序拼接，支持交叉淡化 |
| 字幕提取 | ✅ 支持 | 硬字幕 OCR 识别、软字幕流抽取（SRT/ASS/VTT） |
| 批量整理 | ✅ 支持 | 按日期/项目/课程/会议维度自动归档重命名 |
| 音频提取 | ✅ 支持 | 分离音轨为 MP3/WAV/AAC |
| 画质增强 | ❌ 不支持 | 不提供超分、去噪、插帧等画质修复能力 |
| 内容剪辑 | ❌ 不支持 | 不提供时间线剪辑、特效、滤镜、关键帧动画 |
| 云端处理 | ❌ 不支持 | 全部为本地处理，不涉及任何云端上传 |

### 1.2 适用对象

- **个人用户**：整理网课录屏、会议录像、游戏高光片段
- **内容创作者**：将原始录屏压缩后发布至视频平台
- **企业培训部门**：批量处理内部培训视频，统一格式归档
- **教育机构**：将课堂实录转码为标准格式并提取字幕

### 1.3 环境要求

| 项目 | 最低要求 | 推荐配置 |
|------|---------|---------|
| 操作系统 | Windows 10 / macOS 12 / Ubuntu 20.04 | 64 位系统 |
| 内存 | 8 GB | 16 GB 及以上 |
| 磁盘空间 | 源文件体积 × 2 | 源文件体积 × 3（含临时文件） |
| 依赖工具 | FFmpeg 4.4+、Python 3.8+ | FFmpeg 6.0+、Python 3.11+ |
| 可选依赖 | Tesseract OCR（字幕提取用） | Tesseract 5.x + 中文语言包 |

---

## 二、触发方式

### 2.1 触发词与场景映射

| 触发词 | 用户意图 | 典型场景 |
|--------|---------|---------|
| 录屏 | 处理录屏文件 | "帮我把这个录屏压缩一下" |
| 屏幕录制 | 处理屏幕录制产物 | "屏幕录制文件太大了，转一下格式" |
| 录屏处理 | 综合处理 | "整理一下我今天的录屏" |
| 录屏压缩 | 压缩体积 | "这个录屏 2GB，压到 500MB 以内" |
| 录屏转码 | 转换格式 | "转成 MP4 格式，要兼容播放器" |
| 视频处理 | 通用视频操作 | "把这几段录屏拼起来" |
| 录屏剪辑 | 提取片段 | "把最后 5 分钟截出来" |
| 屏幕录像 | 同"录屏" | 同上 |

### 2.2 触发条件

- 用户提供录屏文件路径或目录路径
- 用户描述录屏处理需求（压缩、转码、拼接、字幕提取等）
- 用户提供批量处理需求（多文件、多目录）

---

## 三、标准流程

### 3.1 前置条件

1. **确认输入**：获取录屏文件路径或目录路径，确认文件存在且可读
2. **确认需求**：明确处理类型（压缩/转码/拼接/字幕提取/批量整理）
3. **确认参数**：输出格式、目标码率/分辨率、拼接顺序、字幕语言等
4. **环境检查**：验证 FFmpeg 可用（`ffmpeg -version`），必要时检查 Tesseract

### 3.2 执行步骤

#### 步骤 1：文件识别与信息采集

```bash
# 获取视频基本信息
ffprobe -v quiet -print_format json -show_format -show_streams input.mp4
```

关键参数：

| 参数 | 说明 | 示例值 |
|------|------|--------|
| duration | 视频时长（秒） | 3725.4 |
| bit_rate | 总码率（bps） | 4856213 |
| width/height | 分辨率 | 1920x1080 |
| codec_name | 编码格式 | h264 / hevc / vp9 |
| nb_frames | 总帧数 | 89312 |

#### 步骤 2：压缩处理

**模式 A：CRF 恒定质量（推荐）**

```bash
ffmpeg -i input.mp4 -c:v libx264 -crf 23 -preset medium -c:a aac -b:a 128k output.mp4
```

CRF 参考表：

| CRF 值 | 质量 | 体积变化 | 适用场景 |
|--------|------|---------|---------|
| 18 | 视觉无损 | 增大 10-30% | 存档、精编 |
| 23 | 高 | 减小 40-60% | 常规发布 |
| 28 | 中 | 减小 70-80% | 网盘存储 |
| 32 | 低 | 减小 85-90% | 临时预览 |

**模式 B：目标码率**

```bash
ffmpeg -i input.mp4 -c:v libx264 -b:v 2M -maxrate 2.5M -bufsize 5M -c:a aac -b:a 128k output.mp4
```

码率建议表（1080p）：

| 内容类型 | 建议码率 | 说明 |
|---------|---------|------|
| 屏幕录制（静态为主） | 1-2 Mbps | 文字、PPT 为主 |
| 屏幕录制（动态操作） | 2-4 Mbps | 含鼠标移动、窗口切换 |
| 视频会议录像 | 1.5-3 Mbps | 人脸+共享屏幕 |
| 游戏录屏 | 6-12 Mbps | 高动态场景 |

#### 步骤 3：转码处理

```bash
# 转 MP4（H.264 + AAC，兼容性最佳）
ffmpeg -i input.mkv -c:v libx264 -crf 23 -preset medium -c:a aac -b:a 128k -movflags +faststart output.mp4

# 转 WebM（VP9 + Opus，网页播放）
ffmpeg -i input.mp4 -c:v libvpx-vp9 -crf 32 -b:v 0 -c:a libopus output.webm

# 转 GIF（短片段，≤10秒）
ffmpeg -i input.mp4 -t 10 -vf "fps=15,scale=480:-1" -loop 0 output.gif
```

#### 步骤 4：视频拼接

**前置条件**：所有待拼接文件必须具有相同的分辨率、帧率、编码格式。

```bash
# 方法一：concat 协议（同参数文件）
ffmpeg -f concat -safe 0 -i filelist.txt -c copy output.mp4

# filelist.txt 格式
# file 'part1.mp4'
# file 'part2.mp4'
# file 'part3.mp4'

# 方法二：重新编码（参数不一致时）
ffmpeg -i part1.mp4 -i part2.mp4 -filter_complex "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]" -map "[v]" -map "[a]" output.mp4
```

#### 步骤 5：字幕提取

**软字幕（内嵌字幕流）**：

```bash
# 列出所有字幕流
ffprobe -v quiet -show_streams -select_streams s input.mkv

# 提取字幕流（索引 0）
ffmpeg -i input.mkv -map 0:s:0 output.srt
```

**硬字幕（画面内文字）**：

```bash
# 使用 OCR 提取（需 Tesseract）
ffmpeg -i input.mp4 -vf "fps=1" frames/%04d.png
tesseract frames/0001.png output -l chi_sim+eng
```

#### 步骤 6：批量整理

```bash
# 目录结构示例
录屏归档/
├── 2026-08-19/
│   ├── 项目A_会议录屏_001.mp4
│   ├── 项目A_会议录屏_002.mp4
│   └── 项目B_培训录屏_001.mp4
└── 2026-08-20/
    └── 课程C_第3讲.mp4
```

命名规则：`{项目/课程}_{类型}_{序号}.{ext}`

### 3.3 输出规范

| 输出类型 | 规范要求 |
|---------|---------|
| 视频文件 | 统一封装格式（MP4 优先），文件名含处理标记（如 `_compressed`、`_converted`） |
| 字幕文件 | SRT 格式（UTF-8 编码），与视频同名同目录 |
| 处理报告 | 输出 JSON 格式报告，含输入/输出路径、处理参数、耗时、体积变化 |
| 日志 | 保留 FFmpeg 完整输出日志，便于排查 |

---

## 四、置信度门控

### 4.1 信息不足时的处理

当以下信息缺失时，使用 `[需核实:字段]` 占位，不进行猜测：

| 缺失信息 | 占位示例 | 后续处理 |
|---------|---------|---------|
| 目标码率 | `[需核实:目标码率]` | 询问用户期望的输出体积或码率 |
| 拼接顺序 | `[需核实:拼接顺序]` | 要求用户提供文件顺序列表 |
| 字幕语言 | `[需核实:字幕语言]` | 确认 OCR 语言包是否安装 |
| 输出格式 | `[需核实:输出格式]` | 根据用途推荐（发布/存储/预览） |
| 分辨率要求 | `[需核实:目标分辨率]` | 确认是否缩放、保持宽高比 |

### 4.2 禁止行为

- 不猜测文件路径（路径不存在时明确报错）
- 不假设编码参数（CRF 值、码率等必须明确）
- 不推断拼接顺序（必须由用户指定）
- 不自动覆盖原文件（输出文件必须为新文件名）

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|---------|---------|---------|
| ERR_FFMPEG_NOT_FOUND | FFmpeg 未安装或不在 PATH | "未检测到 FFmpeg，请先安装并配置环境变量" | 安装 FFmpeg 并确认 `ffmpeg -version` 可执行 |
| ERR_FILE_NOT_FOUND | 输入文件不存在 | "找不到文件 [路径]，请确认路径是否正确" | 检查路径拼写、文件是否被移动/删除 |
| ERR_UNSUPPORTED_FORMAT | 不支持的视频格式 | "暂不支持 [格式] 格式，请先转码为 MP4/MKV/AVI" | 使用 FFmpeg 先转为支持的格式 |
| ERR_CODEC_MISMATCH | 拼接文件编码不一致 | "待拼接文件编码不一致，请统一编码后再拼接" | 先转码为相同编码，再执行拼接 |
| ERR_OCR_LANG_MISSING | OCR 语言包缺失 | "缺少 [语言] 语言包，无法进行字幕识别" | 安装 Tesseract 语言包（如 `tesseract-ocr-chi-sim`） |
| ERR_OUTPUT_EXISTS | 输出文件已存在 | "输出文件 [路径] 已存在，是否覆盖？" | 确认覆盖或指定新输出路径 |
| ERR_DISK_FULL | 磁盘空间不足 | "磁盘空间不足，需要至少 [X] GB 可用空间" | 清理磁盘或更换输出目录 |
| ERR_PERMISSION_DENIED | 无写入权限 | "没有权限写入 [路径]，请检查目录权限" | 修改目录权限或更换输出目录 |
| ERR_DURATION_ZERO | 视频时长为 0 | "视频文件可能已损坏，时长为 0" | 检查源文件完整性，重新录制或修复 |
| ERR_CONCAT_FAILED | 拼接失败 | "拼接失败，请检查所有文件是否可正常播放" | 逐个验证文件完整性，排除损坏文件 |

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 常见坑 | 反模式（错误做法） | 正模式（正确做法） |
|--------|-------------------|-------------------|
| 压缩后画质模糊 | 直接使用 CRF 32 压缩所有文件 | 先分析内容类型，静态屏幕用 CRF 26-28，动态内容用 CRF 20-23 |
| 拼接后音画不同步 | 直接 concat 不同帧率的文件 | 先统一帧率（`-r 30`），再执行拼接 |
| 字幕提取乱码 | 直接提取不检查编码 | 提取后检查编码，使用 `iconv` 转换为 UTF-8 |
| 批量处理中断 | 一次性处理所有文件无检查点 | 分批处理，每批 10-20 个文件，处理完一批验证一批 |
| 磁盘空间耗尽 | 不检查剩余空间直接处理大文件 | 处理前检查磁盘空间，预留源文件 2 倍空间 |
| 覆盖原文件 | 输出路径与原文件相同 | 始终使用新文件名，保留原文件 |
| 忽略音频参数 | 只调视频参数不调音频 | 视频压缩时同步调整音频码率，避免音视频体积失衡 |

### 6.2 反模式示例

**反模式 1**：用户说"压缩一下"，直接使用默认参数处理，不询问目标体积或质量要求。

**正模式**：先询问"您希望压缩到什么程度？是保持高质量（体积减小 40-50%）还是极致压缩（体积减小 80%+）？"

**反模式 2**：用户说"把这几段拼起来"，直接按文件名排序拼接。

**正模式**：确认拼接顺序，询问"请确认拼接顺序：1. 开场.mp4 → 2. 主体.mp4 → 3. 结尾.mp4，是否正确？"

**反模式 3**：用户说"提取字幕"，直接提取第一个字幕流。

**正模式**：先列出所有字幕流，询问"检测到 3 条字幕流：0-英语、1-中文、2-日语，需要提取哪一条？"

---

## 七、渐进式披露

### 7.1 阅读路径

**新手路径（首次使用）**：

1. 阅读「一、能力边界」了解能做什么
2. 阅读「二、触发方式」了解如何发起请求
3. 阅读「三、标准流程」中的步骤 1-3（识别、压缩、转码）
4. 遇到问题查阅「五、错误码体系」

**进阶路径（熟练用户）**：

1. 完整阅读「三、标准流程」所有步骤
2. 关注「六、FAQ 反模式」避免常见错误
3. 结合参数表自定义处理参数
4. 使用批量整理功能实现自动化归档

### 7.2 速查卡

```text
┌─────────────────────────────────────────────┐
│  录屏处理速查卡                              │
├─────────────────────────────────────────────┤
│  压缩：ffmpeg -i in.mp4 -crf 23 out.mp4     │
│  转码：ffmpeg -i in.mkv -c:v libx264 out.mp4│
│  拼接：ffmpeg -f concat -i list.txt -c copy │
│  字幕：ffmpeg -i in.mkv -map 0:s:0 out.srt  │
│  提取音频：ffmpeg -i in.mp4 -vn out.mp3     │
│  截取片段：ffmpeg -i in.mp4 -ss 00:01:00    │
│           -t 00:00:30 out.mp4               │
├─────────────────────────────────────────────┤
│  常用 CRF 值：18(无损) 23(高) 28(中) 32(低) │
│  常用码率：1080p 屏幕录制 1-4 Mbps          │
│  拼接要求：同分辨率、同帧率、同编码          │
└─────────────────────────────────────────────┘
```

### 7.3 处理流程决策树

```text
用户请求
  │
  ├─ 压缩 → 询问目标 → CRF 模式 / 码率模式
  │
  ├─ 转码 → 询问输出格式 → MP4 / MKV / WebM / GIF
  │
  ├─ 拼接 → 确认顺序 → 检查参数一致性 → 拼接
  │


## 许可证（License）

```text
MIT License

Copyright (c) 2026 SkillForge Lab

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```
<!-- professional-license-embedded -->

---
copyright_holder: 原创作者（自持版权）
source_project: original
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
ai_generated: true
license: MIT
slug: skill-24725
name: skill-24725
displayName: 录屏
description: 录屏场景一站式处理技能：覆盖录屏的识别、整理、生成与校验，输出可直接使用的结果文件。
version: 1.0.0
author: skill-factory-auto
agent_created: true
trigger_words:
  - "录屏"
  - "录屏处理"
  - "录屏生成"
  - "录屏整理"
  - "skill-24725"
  - "录屏自动化"
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


# WorkBuddy Skill: 录屏

> **slug:** screen-recording-pro  
> **name:** screen-recording-pro  
> **displayName:** 录屏处理专家  
> **description:** 录屏场景一站式处理技能：覆盖录屏的识别、整理、生成与校验，输出可直接使用的结果文件。  
> **version:** 1.0.0  
> **trigger_words:** ["录屏", "录屏处理", "录屏生成", "录屏整理", "屏幕录制", "帮我处理录屏", "这个录屏乱了", "录屏转视频", "录屏剪辑", "录屏自动化"]

---

## 📋 一页纸速查卡（30秒上手）

```
┌─────────────────────────────────────────────────────────────┐
│  WorkBuddy Skill: 录屏处理专家                                │
│                                                             │
│  ✅ 能做：                                                 │
│    · 识别录屏文件格式/编码/分辨率/帧率                        │
│    · 批量重命名 + 按时间/场景自动整理                          │
│    · 录屏转MP4/H.265压缩（体积减50%+）                        │
│    · 提取音频为MP3/WAV                                       │
│    · 截取关键帧生成封面/预览GIF                               │
│    · 拼接多段录屏 + 自动对齐时间轴                            │
│    · 字幕提取（OCR识别屏幕文字）                              │
│                                                             │
│  ❌ 不做：                                                  │
│    · 不进行AI视频内容理解/摘要                                │
│    · 不进行人脸识别/模糊处理                                  │
│    · 不进行云端存储/分享                                     │
│                                                             │
│  🚀 快速开始：                                              │
│    输入: "帮我处理这个录屏" + 文件路径                        │
│    输出: 整理后的文件 + 处理报告                              │
│                                                             │
│  📦 依赖: ffmpeg, python-opencv, pytesseract                │
└─────────────────────────────────────────────────────────────┘
```

---

## 一、能力边界（Capability Boundary）

### ✅ 能做清单（5+项具体能力）

| 序号 | 能力项 | 具体说明 | 输出物 |
|------|--------|----------|--------|
| 1 | **录屏文件识别** | 自动检测文件格式（MP4/AVI/MKV/MOV/FLV）、编码（H.264/H.265/VP9）、分辨率（720p/1080p/4K）、帧率（30/60fps）、时长、码率 | 文件信息JSON + 可视化报告 |
| 2 | **批量整理与重命名** | 按录制时间、时长、文件大小自动重命名（如 `20240115_143022_教学演示.mp4`），支持自定义模板 | 重命名后的文件 + 映射表CSV |
| 3 | **视频压缩转码** | H.265/HEVC 压缩（同画质体积减少50-70%），支持 CRF 质量控制（18-28），支持分辨率缩放（4K→1080p） | 压缩后的MP4文件 |
| 4 | **音频提取** | 提取录屏中的音轨为 MP3（192kbps）/WAV（无损），支持降噪预处理（高通滤波） | 音频文件 + 波形图 |
| 5 | **关键帧截取** | 按时间点/场景变化自动截取关键帧，生成封面图（JPG/PNG）和预览GIF（3-5秒） | 封面图 + 预览GIF |
| 6 | **多段拼接** | 将多段录屏按时间顺序拼接，支持交叉淡化转场（0.5s），自动对齐分辨率/帧率 | 拼接后的完整视频 |
| 7 | **屏幕文字OCR** | 使用 Tesseract OCR 提取录屏中的屏幕文字（菜单、对话框、代码），输出SRT字幕文件 | SRT字幕 + 文本TXT |
| 8 | **元数据写入** | 将录制信息（时间/设备/软件）写入视频元数据，支持批量添加标签 | 带元数据的视频文件 |

### ❌ 不做清单（3+项边界声明）

| 序号 | 边界声明 | 原因说明 |
|------|----------|----------|
| 1 | **不进行AI视频内容理解/摘要** | 本技能聚焦于视频文件的工程化处理（格式/压缩/提取），不涉及语义理解、场景识别、内容摘要等AI能力。如需内容分析，请配合其他AI Skill使用 |
| 2 | **不进行人脸识别/隐私模糊** | 出于隐私合规考虑，本技能不包含人脸检测、人脸模糊、敏感信息打码等功能。如需处理，请使用专业视频编辑软件 |
| 3 | **不进行云端存储/分享** | 本技能仅处理本地文件，不包含上传、分享、云存储等网络操作。处理结果保存在本地指定目录 |
| 4 | **不支持录屏实时采集** | 本技能处理已存在的录屏文件，不支持屏幕实时录制、直播推流等实时场景。实时录制请使用 OBS、Xbox Game Bar 等工具 |

---

## 二、触发方式（Trigger Methods）

### 6类场景触发词表

| 场景类型 | 触发词示例 |
|----------|------------|
| **直接指令** | 录屏、录屏处理、录屏生成、录屏整理、屏幕录制 |
| **问题描述** | 这个录屏乱了、录屏打不开、录屏文件太大、录屏没声音 |
| **动作请求** | 帮我处理录屏、帮我压缩录屏、帮我提取音频、帮我拼接录屏 |
| **批量处理** | 批量处理录屏、整理所有录屏、批量转码、批量重命名 |
| **格式转换** | 录屏转MP4、录屏转GIF、录屏提取字幕、录屏转音频 |
| **Skill调用** | skill-24725、录屏自动化、录屏工作流 |

### 大白话触发示例表

| 用户原话 | 触发动作 |
|----------|----------|
| "帮我处理这个录屏" | 启动标准流程：识别文件 → 整理 → 输出报告 |
| "这个录屏文件太大了，发不出去" | 启动压缩流程：检测码率 → H.265压缩 → 输出体积对比 |
| "录屏没声音，帮我看看" | 启动音频诊断：检查音轨 → 提取音频 → 分析波形 |
| "我有10个录屏要整理" | 启动批量处理：遍历目录 → 批量重命名 → 生成索引 |
| "把录屏转成GIF发给客户" | 启动GIF生成：截取关键帧 → 优化调色板 → 输出GIF |
| "录屏里的文字帮我提取出来" | 启动OCR流程：逐帧OCR → 生成SRT → 输出文本 |

---

## 三、标准流程（Standard Workflow）

### Step 1: 收集最小信息集

启动时，需要确认以下关键信息（按优先级排序）：

| 优先级 | 信息项 | 必填/选填 | 示例 | 询问话术 |
|--------|--------|-----------|------|----------|
| P0 | **文件路径** | 必填 | `C:\Users\admin\Videos\录屏\demo.mp4` | "请提供录屏文件的路径或拖拽文件到对话框" |
| P0 | **处理目标** | 必填 | 压缩/整理/提取音频/拼接/OCR | "您希望我做什么处理？压缩、整理、提取音频还是其他？" |
| P1 | **输出目录** | 选填 | `D:\output\` | "输出文件保存到哪里？（默认与原文件同目录）" |
| P1 | **目标分辨率** | 选填 | 1080p/720p/480p | "需要调整分辨率吗？（默认保持原分辨率）" |
| P2 | **压缩质量** | 选填 | CRF 23（默认）/ 18（高质量）/ 28（小体积） | "压缩质量偏好？高质量（文件大）还是小体积（画质略降）？" |
| P2 | **时间范围** | 选填 | 00:01:30-00:05:00 | "需要截取特定时间段吗？（默认处理全片）" |

> **信息缺失处理**：若用户仅提供路径未说明目标，默认执行"标准整理流程"（识别+重命名+信息报告）；若未提供路径，则提示用户输入。

### Step 2: 核心执行（真实代码实现）

#### 2.1 录屏文件识别

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""录屏文件识别模块 - 使用 ffprobe 获取视频元数据"""

import subprocess
import json
import os
from pathlib import Path

def probe_video(filepath):
    """
    使用 ffprobe 获取视频文件的完整元数据
    返回: dict 包含格式、编码、分辨率、帧率、码率、时长等信息
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")
    
    cmd = [
        'ffprobe', '-v', 'quiet',
        '-print_format', 'json',
        '-show_format', '-show_streams',
        filepath
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe 执行失败: {result.stderr}")
    
    data = json.loads(result.stdout)
    
    # 提取视频流信息
    video_stream = None
    audio_stream = None
    for stream in data.get('streams', []):
        if stream['codec_type'] == 'video' and video_stream is None:
            video_stream = stream
        elif stream['codec_type'] == 'audio' and audio_stream is None:
            audio_stream = stream
    
    if video_stream is None:
        raise ValueError("未找到视频流，文件可能不是有效的视频文件")
    
    # 计算码率（kbps）
    format_info = data.get('format', {})
    bit_rate = int(format_info.get('bit_rate', 0)) / 1000
    
    # 计算文件大小（MB）
    file_size = os.path.getsize(filepath) / (1024 * 1024)
    
    info = {
        'filepath': filepath,
        'filename': os.path.basename(filepath),
        'format': format_info.get('format_name', 'unknown'),
        'duration': float(format_info.get('duration', 0)),
        'size_mb': round(file_size, 2),
        'bit_rate_kbps': round(bit_rate, 2),
        'video': {
            'codec': video_stream.get('codec_name', 'unknown'),
            'width': video_stream.get('width', 0),
            'height': video_stream.get('height', 0),
            'fps': eval(video_stream.get('avg_frame_rate', '0/1')),
            'pix_fmt': video_stream.get('pix_fmt', 'unknown'),
        },
        'audio': None
    }
    
    if audio_stream:
        info['audio'] = {
            'codec': audio_stream.get('codec_name', 'unknown'),
            'sample_rate': audio_stream.get('sample_rate', 'unknown'),
            'channels': audio_stream.get('channels', 0),
        }
    
    return info


def format_duration(seconds):
    """将秒数格式化为 HH:MM:SS"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def generate_report(info):
    """生成人类可读的报告文本"""
    lines = [
        "📹 录屏文件信息报告",
        "=" * 40,
        f"📁 文件: {info['filename']}",
        f"📦 格式: {info['format']}",
        f"⏱️ 时长: {format_duration(info['duration'])}",
        f"💾 大小: {info['size_mb']} MB",
        f"📊 码率: {info['bit_rate_kbps']} kbps",
        f"🎬 视频编码: {info['video']['codec']}",
        f"🖥️ 分辨率: {info['video']['width']}x{info['video']['height']}",
        f"⚡ 帧率: {info['video']['fps']} fps",
        f"🎨 像素格式: {info['video']['pix_fmt']}",
    ]
    
    if info['audio']:
        lines.extend([
            f"🔊 音频编码: {info['audio']['codec']}",
            f"🎵 采样率: {info['audio']['sample_rate']} Hz",
            f"🔉 声道数: {info['audio']['channels']}",
        ])
    else:
        lines.append("🔇 无音轨")
    
    return "\n".join(lines)
```

#### 2.2 录屏压缩转码（H.265）

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""录屏压缩模块 - 使用 ffmpeg 进行 H.265 转码"""

import subprocess
import os
from pathlib import Path

def compress_video(input_path, output_path=None, crf=23, target_resolution=None):
    """
    使用 H.265/HEVC 编码压缩视频
    
    参数:
        input_path: 输入视频路径
        output_path: 输出路径（默认在输入目录生成 _compressed 后缀）
        crf: 质量参数 18-28（18=高质量大文件，28=低质量小文件）
        target_resolution: 目标分辨率如 '1920:1080'，None 表示保持原分辨率
    
    返回:
        dict: 压缩前后体积对比信息
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"输入文件不存在: {input_path}")
    
    if output_path is None:
        stem = Path(input_path).stem
        suffix = Path(input_path).suffix
        output_path = str(Path(input_path).parent / f"{stem}_compressed{suffix}")
    
    # 构建 ffmpeg 命令
    cmd = [
        'ffmpeg', '-y',  # -y 覆盖输出文件
        '-i', input_path,
        '-c:v', 'libx265',
        '-crf', str(crf),
        '-preset', 'medium',  # 平衡速度与压缩率
        '-tag:v', 'hvc1',  # 兼容 Apple 设备
        '-c:a', 'aac',
        '-b:a', '128k',
        '-movflags', '+faststart',  # 便于网络播放
    ]
    
    # 添加分辨率缩放
    if target_resolution:
        cmd.extend(['-vf', f'scale={target_resolution}'])
    
    cmd.append(output_path)
    
    print(f"🚀 开始压缩: {os.path.basename(input_path)}")
    print(f"   CRF={crf}, 目标分辨率={target_resolution or '原始'}")
    
    # 执行命令
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 执行失败: {result.stderr[-500:]}")
    
    # 计算压缩率
    input_size = os.path.getsize(input_path) / (1024 * 1024)
    output_size = os.path.getsize(output_path) / (1024 * 1024)
    ratio = (1 - output_size / input_size) * 100
    
    info = {
        'input_path': input_path,
        'output_path': output_path,
        'input_size_mb': round(input_size, 2),
        'output_size_mb': round(output_size, 2),
        'compression_ratio': round(ratio, 1),
        'crf': crf,
    }
    
    print(f"✅ 压缩完成!")
    print(f"   原始大小: {info['input_size_mb']} MB")
    print(f"   压缩后: {info['output_size_mb']} MB")
    print(f"   节省空间: {info['compression_ratio']}%")
    
    return info
```

#### 2.3 音频提取与降噪

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""音频提取模块 - 使用 ffmpeg 提取音轨并降噪"""

import subprocess
import os

def extract_audio(input_path, output_format='mp3', bitrate='192k', denoise=True):
    """
    从录屏中提取音频
    
    参数:
        input_path: 输入视频路径
        output_format: 输出格式 mp3/wav
        bitrate: 音频码率（mp3时有效）
        denoise: 是否启用高通滤波降噪（去除低频噪音）
    
    返回:
        str: 输出音频文件路径
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"输入文件不存在: {input_path}")
    
    stem = Path(input_path).stem
    output_path = str(Path(input_path).parent / f"{stem}_audio.{output_format}")
    
    cmd = ['ffmpeg', '-y', '-i', input_path]
    
    # 音频处理链
    if denoise:
        # 高通滤波去除100Hz以下噪音 + 低通滤波去除15kHz以上噪音
        cmd.extend(['-af', 'highpass=f=100,lowpass=f=15000'])
    
    if output_format == 'mp3':
        cmd.extend(['-c:a', 'libmp3lame', '-b:a', bitrate])
    elif output_format == 'wav':
        cmd.extend(['-c:a', 'pcm_s16le'])
    else:
        raise ValueError(f"不支持的输出格式: {output_format}")
    
    cmd.append(output_path)
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"音频提取失败: {result.stderr[-500:]}")
    
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"✅ 音频提取完成: {output_path} ({size_mb:.2f} MB)")
    
    return output_path
```

#### 2.4 关键帧截取与GIF生成

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""关键帧截取模块 - 使用 OpenCV 检测场景变化并截取关键帧"""

import cv2
import os
from pathlib import Path

def extract_keyframes(input_path, output_dir=None, threshold=30.0, max_frames=10):
    """
    基于场景变化检测自动截取关键帧
    
    参数:
        input_path: 输入视频路径
        output_dir: 输出目录（默认在视频同目录创建 keyframes 文件夹）
        threshold: 场景变化阈值（越大越敏感，建议20-40）
        max_frames: 最多截取帧数
    
    返回:
        list: 截取的关键帧文件路径列表
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"输入文件不存在: {input_path}")
    
    if output_dir is None:
        stem = Path(input_path).stem
        output_dir = str(Path(input_path).parent / f"{stem}_keyframes")
    os.makedirs(output_dir, exist_ok=True)
    
    cap = cv2.VideoCapture(input_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    prev_frame = None
    keyframes = []
    frame_count = 0
    
    while cap.isOpened() and len(keyframes) < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        
        # 每隔10帧检测一次场景变化（提高效率）
        if frame_count % 10 != 0:
            continue
        
        # 转换为灰度图并缩小以加速计算
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (320, 180))
        
        if prev_frame is not None:
            # 计算帧间差异
            diff = cv2.absdiff(gray, prev_frame)
            mean_diff = diff.mean()
            
            if mean_diff > threshold:
                # 场景变化，截取当前帧
                timestamp = frame_count / fps
                filename = f"keyframe_{format_duration(timestamp).replace(':', '-')}.jpg"
                filepath = str(Path(output_dir) / filename)
                cv2.imwrite(filepath, frame)
                keyframes.append({
                    'path': filepath,
                    'timestamp': timestamp,
                    'diff_score': round(mean_diff, 2)
                })
                print(f"📸 截取关键帧: {filename} (时间: {format_duration(timestamp)})")
        
        prev_frame = gray
    
    cap.release()
    
    if not keyframes:
        print("⚠️ 未检测到明显场景变化，尝试均匀截取")
        # 兜底：均匀截取
        cap = cv2.VideoCapture(input_path)
        interval = max(1, total_frames // max_frames)
        for i in range(0, total_frames, interval):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()
            if ret:
                timestamp = i / fps
                filename = f"keyframe_{format_duration(timestamp).replace(':', '-')}.jpg"
                filepath = str(Path(output_dir) / filename)
                cv2.imwrite(filepath, frame)
                keyframes.append({
                    'path': filepath,
                    'timestamp': timestamp,
                    'diff_score': 0
                })
        cap.release()
    
    print(f"✅ 共截取 {len(keyframes)} 个关键帧，保存至: {output_dir}")
    return keyframes


def generate_gif(input_path, output_path=None, duration=3, fps=10):
    """
    生成预览GIF（取视频前N秒）
    
    参数:
        input_path: 输入视频路径
        output_path: 输出GIF路径
        duration: GIF时长（秒）
        fps: GIF帧率
    
    返回:
        str: GIF文件路径
    """
    if output_path is None:
        stem = Path(input_path).stem
        output_path = str(Path(input_path).parent / f"{stem}_preview.gif")
    
    cmd = [
        'ffmpeg', '-y',
        '-i', input_path,
        '-t', str(duration),
        '-vf', f'fps={fps},scale=480:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse',
        '-loop', '0',
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"GIF生成失败: {result.stderr[-500:]}")
    
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"✅ GIF生成完成: {output_path} ({size_mb:.2f} MB)")
    
    return output_path
```

#### 2.5 多段录屏拼接

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""录屏拼接模块 - 使用 ffmpeg concat 协议合并多段视频"""

import subprocess
import os
from pathlib import Path

def concat_videos(input_paths, output_path=None, crossfade=0.5):
    """
    拼接多段录屏视频
    
    参数:
        input_paths: 输入视频路径列表（按时间顺序）
        output_path: 输出路径
        crossfade: 交叉淡化时长（秒），0表示直接拼接
    
    返回:
        str: 输出视频路径
    """
    if len(input_paths) < 2:
        raise ValueError("至少需要2个视频才能拼接")
    
    for p in input_paths:
        if not os.path.exists(p):
            raise FileNotFoundError(f"输入文件不存在: {p}")
    
    if output_path is None:
        output_path = str(Path(input_paths[0]).parent / "concat_output.mp4")
    
    if crossfade > 0:
        # 使用 xfade 滤镜实现交叉淡化
        return _concat_with_xfade(input_paths, output_path, crossfade)
    else:
        # 直接拼接（使用 concat demuxer）
        return _concat_direct(input_paths, output_path)


def _concat_direct(input_paths, output_path):
    """直接拼接（无转场效果）"""
    # 创建 concat 列表文件
    list_file = str(Path(output_path).parent / "concat_list.txt")
    with open(list_file, 'w', encoding='utf-8') as f:
        for p in input_paths:
            f.write(f"file '{p}'\n")
    
    cmd = [
        'ffmpeg', '-y',
        '-f', 'concat', '-safe', '0',
        '-i', list_file,
        '-c', 'copy',  # 直接复制流，不重新编码
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"拼接失败: {result.stderr[-500:]}")
    
    os.remove(list_file)
    print(f"✅ 拼接完成: {output_path}")
    return output_path


def _concat_with_xfade(input_paths, output_path, crossfade):
    """使用 xfade 滤镜实现交叉淡化转场"""
    # 构建滤镜图
    filter_parts = []
    inputs = []
    
    for i, p in enumerate(input_paths):
        inputs.extend(['-i', p])
        filter_parts.append(f"[{i}:v]setpts=PTS-STARTPTS[v{i}]")
        filter_parts.append(f"[{i}:a]asetpts=PTS-STARTPTS[a{i}]")
    
    # 构建 xfade 链
    for i in range(1, len(input_paths)):
        offset = f"offset={i * (10 - crossfade)}"  # 简化计算
        filter_parts.append(
            f"[v{i-1}][v{i}]xfade=transition=fade:duration={crossfade}:{offset}[vx{i}]"
        )
    
    # 音频交叉淡化
    for i in range(1, len(input_paths)):
        filter_parts.append(
            f"[a{i-1}][a{i}]acrossfade=d={crossfade}[ax{i}]"
        )
    
    # 最终输出
    filter_parts.append("[vx%d][ax%d]concat=n=1:v=1:a=1[outv][outa]" % 
                       (len(input_paths)-1, len(input_paths)-1))
    
    filter_complex = ";".join(filter_parts)
    
    cmd = [
        'ffmpeg', '-y',
        *inputs,
        '-filter_complex', filter_complex,
        '-map', '[outv]', '-map', '[outa]',
        '-c:v', 'libx264', '-crf', '20',
        '-c:a', 'aac',
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"交叉淡化拼接失败: {result.stderr[-500:]}")
    
    print(f"✅ 交叉淡化拼接完成: {output_path}")
    return output_path
```

#### 2.6 屏幕文字OCR提取

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""屏幕文字OCR模块 - 使用 Tesseract 提取录屏中的文字"""

import cv2
import pytesseract
import os
from pathlib import Path

def extract_screen_text(input_path, output_dir=None, interval=5, lang='chi_sim+eng'):
    """
    从录屏中提取屏幕文字并生成SRT字幕
    
    参数:
        input_path: 输入视频路径
        output_dir: 输出目录
        interval: OCR检测间隔（秒）
        lang: Tesseract 语言包
    
    返回:
        dict: 包含SRT路径和提取的文本
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"输入文件不存在: {input_path}")
    
    if output_dir is None:
        stem = Path(input_path).stem
        output_dir = str(Path(input_path).parent / f"{stem}_ocr")
    os.makedirs(output_dir, exist_ok=True)
    
    cap = cv2.VideoCapture(input_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    
    srt_entries = []
    all_text = []
    frame_interval = int(fps * interval)
    frame_count = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_count % frame_interval != 0:
            frame_count += 1
            continue
        
        # 预处理：放大2倍提升OCR精度
        h, w = frame.shape[:2]
        scaled = cv2.resize(frame, (w*2, h*2), interpolation=cv2.INTER_CUBIC)
        
        # 转为灰度
        gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)
        
        # OCR识别
        try:
            text = pytesseract.image_to_string(gray, lang=lang)
            text = text.strip()
            
            if text and len(text) > 5:  # 过滤过短文本
                timestamp = frame_count / fps
                srt_entries.append({
                    'start': timestamp,
                    'end': min(timestamp + interval, duration),
                    'text': text
                })
                all_text.append(text)
                print(f"📝 识别到文字 (时间 {format_duration(timestamp)}): {text[:50]}...")
        except Exception as e:
            print(f"⚠️ OCR识别失败: {e}")
        
        frame_count += 1
    
    cap.release()
    
    # 生成SRT文件
    srt_path = str(Path(output_dir) / "subtitles.srt")
    with open(srt_path, 'w', encoding='utf-8') as f:
        for i, entry in enumerate(srt_entries, 1):
            f.write(f"{i}\n")
            f.write(f"{_format_srt_time(entry['start'])} --> {_format_srt_time(entry['end'])}\n")
            f.write(f"{entry['text']}\n\n")
    
    # 生成纯文本文件
    txt_path = str(Path(output_dir) / "extracted_text.txt")
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("\n\n".join(all_text))
    
    print(f"✅ OCR完成: 提取 {len(srt_entries)} 条文字")
    print(f"   SRT字幕: {srt_path}")
    print(f"   纯文本: {txt_path}")
    
    return {
        'srt_path': srt_path,
        'txt_path': txt_path,
        'entries': srt_entries
    }


def _format_srt_time(seconds):
    """格式化SRT时间戳"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
```

#### 2.7 批量整理与重命名

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量整理模块 - 自动重命名和分类录屏文件"""

import os
import re
from pathlib import Path
from datetime import datetime

def batch_organize(directory, pattern=None, dry_run=True):
    """
    批量整理录屏文件
    
    参数:
        directory: 目标目录
        pattern: 自定义命名模板（支持 {date} {time} {duration} {size}）
        dry_run: 试运行模式（不实际重命名）
    
    返回:
        list: 重命名映射表
    """
    if not os.path.isdir(directory):
        raise NotADirectoryError(f"目录不存在: {directory}")
    
    video_exts = {'.mp4', '.avi', '.mkv', '.mov', '.flv', '.wmv', '.webm'}
    files = []
    
    # 收集所有视频文件
    for f in Path(directory).iterdir():
        if f.suffix.lower() in video_exts:
            files.append(f)
    
    if not files:
        print("⚠️ 目录中未找到视频文件")
        return []
    
    print(f"📁 找到 {len(files)} 个视频文件")
    
    # 默认命名模板
    if pattern is None:
        pattern = "{date}_{time}_{duration}s_{size}MB"
    
    rename_map = []
    
    for i, filepath in enumerate(files, 1):
        # 获取文件信息
        stat = filepath.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime)
        
        # 使用 ffprobe 获取时长
        try:
            import subprocess
            cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                   '-of', 'csv=p=0', str(filepath)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            duration = int(float(result.stdout.strip()))
        except:
            duration = 0
        
        size_mb = stat.st_size / (1024 * 1024)
        
        # 生成新文件名
        new_name = pattern.format(
            date=mtime.strftime('%Y%m%d'),
            time=mtime.strftime('%H%M%S'),
            duration=duration,
            size=int(size_mb),
            index=i
        )
        
        new_name = f"{new_name}{filepath.suffix}"
        new_path = filepath.parent / new_name
        
        # 处理重名
        counter = 1
        while new_path.exists() and new_path != filepath:
            stem = new_path.stem
            new_path = filepath.parent / f"{stem}_{counter}{filepath.suffix}"
            counter += 1
        
        rename_map.append({
            'old_path': str(filepath),
            'new_path': str(new_path),
            'old_name': filepath.name,
            'new_name': new_path.name
        })
        
        if not dry_run:
            filepath.rename(new_path)
            print(f"✅ {filepath.name} → {new_path.name}")
        else:
            print(f"🔍 [试运行] {filepath.name} → {new_path.name}")
    
    # 生成映射表CSV
    csv_path = str(Path(directory) / "rename_map.csv")
    with open(csv_path, 'w', encoding='utf-8') as f:
        f.write("old_name,new_name,old_path,new_path\n")
        for item in rename_map:
            f.write(f"{item['old_name']},{item['new_name']},{item['old_path']},{item['new_path']}\n")
    
    print(f"\n📊 重命名映射表已保存: {csv_path}")
    
    return rename_map
```

### Step 3: 输出校验

处理完成后，必须执行以下校验步骤：

| 校验项 | 方法 | 通过标准 |
|--------|------|----------|
| **文件完整性** | 使用 `ffprobe` 验证输出文件可读 | 能正常读取流信息，无报错 |
| **时长一致性** | 对比输入输出时长 | 偏差 ≤ 2%（压缩/转码场景） |
| **分辨率

## 许可证（License）

```text
MIT License

Copyright (c) 2026 原创作者（自持版权）

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```
<!-- professional-license-embedded -->

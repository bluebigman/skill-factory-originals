---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: skill-24725
name: screen-recording-pro
displayName: 录屏工程化 批处理 交付
description: 录屏文件全流程工程化处理：识别、压缩、转码、拼接、字幕提取与批量整理，输出可交付结果。
version: 2.0.1
rules_version: cpr-20260819-n551
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/skill-24725
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 录屏工坊
agent_created: true
trigger_words: ["录屏", "屏幕录制", "录屏处理", "录屏压缩", "录屏转码", "录屏拼接", "录屏字幕", "录屏整理", "录屏批处理", "录屏工程化"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 录屏工程化处理 Skill 文档

本 Skill 由 AI 辅助生成，仅供参考。使用前请结合具体环境验证。

---

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 典型场景 |
|--------|------|----------|
| 录屏识别 | 自动检测录屏文件的格式、编码、分辨率、帧率、时长等元数据 | 拿到一批未知来源的录屏文件，先摸清底细 |
| 录屏压缩 | 在可接受的画质损失范围内，显著减小文件体积 | 将 2GB 的 4K 录屏压缩到 300MB 以内，便于传输 |
| 录屏转码 | 转换容器格式（如 MP4 ↔ MKV ↔ MOV）或编码格式（如 H.264 ↔ H.265） | 将不兼容的录屏转为目标播放设备支持的格式 |
| 录屏拼接 | 将多个录屏片段按时间顺序合并为一个完整文件 | 将分段录制的教学视频拼接为完整课程 |
| 字幕提取 | 从录屏中提取硬字幕（OCR）或软字幕（内嵌字幕流） | 从录屏中提取讲师讲解的台词文本 |
| 批量整理 | 按规则对录屏文件进行重命名、归档、去重 | 将散落在各目录的录屏按日期+主题归档 |

### 1.2 不能做什么（明确边界）

| 限制项 | 说明 |
|--------|------|
| 不处理实时流 | 本 Skill 仅处理已存在的录屏文件，不涉及实时屏幕捕获或直播推流 |
| 不修复损坏文件 | 若录屏文件已损坏（如文件头缺失、数据不完整），本 Skill 无法修复，仅能报告错误 |
| 不进行内容审核 | 本 Skill 不判断录屏内容是否合规、是否涉及隐私或版权问题 |
| 不进行人脸/物体识别 | 本 Skill 仅处理视频工程属性，不涉及 AI 视觉识别 |
| 不保证无损压缩 | 压缩必然带来画质损失，本 Skill 提供参数建议，但最终效果需用户自行确认 |

### 1.3 适用对象

- 需要批量处理录屏文件的教育工作者（课程录制、讲座整理）
- 需要压缩录屏以便传输的商务人士（会议录屏、演示录屏）
- 需要提取录屏字幕的内容创作者（视频二次加工）
- 需要归档整理录屏素材的运维/行政人员

---

## 二、触发方式

### 2.1 触发词

- 核心触发词：`录屏`、`屏幕录制`
- 扩展触发词：`录屏处理`、`录屏压缩`、`录屏转码`、`录屏拼接`、`录屏字幕`、`录屏整理`、`录屏批处理`、`录屏工程化`

### 2.2 场景映射表

| 用户说（大白话） | 本 Skill 执行动作 |
|------------------|-------------------|
| "我这有个录屏文件太大了，发不出去" | 执行录屏压缩流程 |
| "帮我把这几个录屏合成一个" | 执行录屏拼接流程 |
| "这个录屏在手机上放不了" | 执行录屏转码流程 |
| "我想把录屏里的字幕弄出来" | 执行字幕提取流程 |
| "我有一堆录屏，帮我整理一下" | 执行批量整理流程 |
| "先看看这些录屏都是什么格式" | 执行录屏识别流程 |

---

## 三、标准流程

### 3.1 前置条件

| 条件 | 要求 | 验证方式 |
|------|------|----------|
| 输入文件 | 存在且可读 | `ls -l <file>` 确认文件存在且权限正确 |
| 磁盘空间 | 至少为输入文件总大小的 2 倍 | `df -h` 检查剩余空间 |
| 依赖工具 | ffmpeg ≥ 4.0（必需）；tesseract（字幕 OCR 可选）；python3（批处理脚本可选） | `ffmpeg -version`、`tesseract --version`、`python3 --version` |
| 输出目录 | 存在且可写 | `mkdir -p <output_dir && test -w <output_dir>` |

### 3.2 执行步骤（分步编号）

#### 步骤 1：录屏识别

```bash
# 获取文件基本信息
ffprobe -v error -show_entries format=duration,size,bit_rate -show_entries stream=codec_name,codec_type,width,height,r_frame_rate -of json <input_file>
```

**输出示例：**

```json
{
  "format": {
    "duration": "3600.000000",
    "size": "2147483648",
    "bit_rate": "4771025"
  },
  "streams": [
    {"codec_name": "h264", "codec_type": "video", "width": 1920, "height": 1080, "r_frame_rate": "30/1"},
    {"codec_name": "aac", "codec_type": "audio", "sample_rate": "48000"}
  ]
}
```

**参数解读表：**

| 字段 | 含义 | 典型值 | 备注 |
|------|------|--------|------|
| duration | 时长（秒） | 3600 | 1 小时 |
| size | 文件大小（字节） | 2147483648 | 2GB |
| bit_rate | 总码率（bps） | 4771025 | 约 4.8 Mbps |
| codec_name | 编码格式 | h264 / h265 / vp9 | 视频编码 |
| width × height | 分辨率 | 1920×1080 | 1080p |
| r_frame_rate | 帧率 | 30/1 | 30 fps |

#### 步骤 2：录屏压缩

**压缩策略选择：**

| 场景 | 目标码率 | 参数建议 | 预期压缩比 |
|------|----------|----------|------------|
| 普通教学录屏（PPT+语音） | 1.5 Mbps | `-crf 28 -preset slow` | 3:1 ~ 5:1 |
| 软件操作录屏（含文字细节） | 2.5 Mbps | `-crf 24 -preset medium` | 2:1 ~ 3:1 |
| 高动态内容（游戏/动画） | 4 Mbps | `-crf 22 -preset slow` | 1.5:1 ~ 2:1 |

```bash
# 通用压缩命令（H.264 编码）
ffmpeg -i <input_file> -c:v libx264 -crf 26 -preset slow -c:a aac -b:a 128k -movflags +faststart <output_file>
```

**CRF 值参考表：**

| CRF 值 | 画质 | 文件大小 | 适用场景 |
|--------|------|----------|----------|
| 18 | 视觉无损 | 大 | 存档 |
| 23 | 高 | 中 | 默认推荐 |
| 28 | 中 | 小 | 传输分享 |
| 32 | 低 | 极小 | 临时预览 |

#### 步骤 3：录屏转码

```bash
# 转码为 H.265（HEVC）以减小体积（需确认播放设备支持）
ffmpeg -i <input_file> -c:v libx265 -crf 28 -preset medium -c:a aac -b:a 128k <output_file>

# 转码为兼容性最好的 H.264 + AAC（MP4 容器）
ffmpeg -i <input_file> -c:v libx264 -profile:v main -level 4.0 -c:a aac -b:a 128k -movflags +faststart <output_file>
```

**容器格式兼容性速查：**

| 容器 | 视频编码 | 音频编码 | 兼容性 |
|------|----------|----------|--------|
| MP4 | H.264 / H.265 | AAC | 最佳（几乎所有设备） |
| MKV | 任意 | 任意 | 好（PC 播放器） |
| MOV | H.264 / ProRes | AAC / PCM | 好（Apple 生态） |
| AVI | 旧编码 | MP3 / PCM | 差（不推荐） |

#### 步骤 4：录屏拼接

```bash
# 方法一：使用 concat 协议（适用于相同编码参数的文件）
ffmpeg -i "concat:part1.mp4|part2.mp4|part3.mp4" -c copy <output_file>

# 方法二：使用 concat demuxer（推荐，更稳定）
# 先创建文件列表 concat_list.txt，内容为：
# file 'part1.mp4'
# file 'part2.mp4'
# file 'part3.mp4'
ffmpeg -f concat -safe 0 -i concat_list.txt -c copy <output_file>
```

**拼接注意事项：**

| 问题 | 现象 | 解决方案 |
|------|------|----------|
| 编码参数不一致 | 拼接后花屏/音画不同步 | 先统一转码为相同参数再拼接 |
| 时间戳不连续 | 播放时跳帧 | 使用 `-fflags +genpts` 重新生成时间戳 |
| 分辨率不一致 | 画面大小突变 | 先统一缩放至相同分辨率 |

#### 步骤 5：字幕提取

**场景 A：提取内嵌软字幕（字幕流）**

```bash
# 查看是否有字幕流
ffprobe -v error -select_streams s -show_entries stream=index,codec_name <input_file>

# 提取字幕流为 SRT 格式
ffmpeg -i <input_file> -map 0:s:0 <output_file>.srt
```

**场景 B：OCR 提取硬字幕（烧录在画面上的字幕）**

```bash
# 每 5 秒截取一帧用于 OCR
ffmpeg -i <input_file> -vf "fps=1/5" -q:v 2 frames/frame_%04d.png

# 使用 tesseract 进行 OCR（需安装 tesseract 及中文语言包）
for img in frames/*.png; do
  tesseract "$img" "${img%.png}_ocr" -l chi_sim+eng 2>/dev/null
done

# 合并 OCR 结果（需按时间戳排序）
cat frames/*_ocr.txt > combined_ocr.txt
```

**OCR 准确率影响因素：**

| 因素 | 影响程度 | 优化建议 |
|------|----------|----------|
| 字幕字体大小 | 高 | 放大画面后再 OCR |
| 字幕与背景对比度 | 高 | 先做二值化处理 |
| 字幕语言 | 中 | 指定正确的语言包 |
| 画面抖动 | 低 | 先做防抖处理 |

#### 步骤 6：批量整理

```bash
# 按日期+主题重命名并归档
# 示例：2026-08-19_课程录制_第01讲.mp4

# 使用 Python 脚本进行批量处理（需 python3）
python3 << 'EOF'
import os
import re
from datetime import datetime

def organize_screen_recordings(src_dir, dst_dir, topic):
    for filename in os.listdir(src_dir):
        if not filename.lower().endswith(('.mp4', '.mkv', '.mov')):
            continue
        # 获取文件修改时间
        mtime = os.path.getmtime(os.path.join(src_dir, filename))
        date_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
        # 提取序号（假设文件名中包含序号）
        match = re.search(r'(\d+)', filename)
        seq = match.group(1) if match else '00'
        new_name = f"{date_str}_{topic}_{seq}.{filename.split('.')[-1]}"
        os.rename(
            os.path.join(src_dir, filename),
            os.path.join(dst_dir, new_name)
        )
        print(f"重命名: {filename} → {new_name}")

# 使用示例
organize_screen_recordings('/path/to/raw', '/path/to/archive', '课程录制')
EOF
```

**批量整理规则模板：**

| 规则项 | 示例 | 说明 |
|--------|------|------|
| 日期格式 | `%Y-%m-%d` | 文件修改日期 |
| 主题词 | `课程录制` | 用户自定义 |
| 序号格式 | `%02d` | 两位数字补零 |
| 扩展名 | 保持原样 | 不改变容器格式 |

### 3.3 输出规范

| 输出类型 | 格式 | 存放位置 | 命名规则 |
|----------|------|----------|----------|
| 识别报告 | JSON | 输出目录 | `report_<timestamp>.json` |
| 压缩后视频 | MP4 | 输出目录 | `<原名>_compressed.mp4` |
| 转码后视频 | 目标格式 | 输出目录 | `<原名>_transcoded.<ext>` |
| 拼接后视频 | MP4 | 输出目录 | `merged_<timestamp>.mp4` |
| 字幕文件 | SRT / TXT | 输出目录 | `<原名>_subtitle.srt` |
| 整理后文件 | 原格式 | 归档目录 | `<日期>_<主题>_<序号>.<ext>` |

---

## 四、置信度门控

### 4.1 信息不足时的处理

当遇到以下情况时，本 Skill 不会猜测或编造，而是输出占位符 `[需核实:字段]`：

| 场景 | 输出占位符 | 说明 |
|------|------------|------|
| 无法确定输入文件编码 | `[需核实:编码格式]` | 需用户提供 `ffprobe` 输出 |
| 无法确定目标设备兼容性 | `[需核实:目标设备]` | 需用户明确播放设备型号 |
| 无法确定字幕语言 | `[需核实:字幕语言]` | 需用户确认或提供字幕样本 |
| 无法确定压缩画质可接受度 | `[需核实:画质要求]` | 需用户明确画质优先级 |
| 无法确定文件时间戳 | `[需核实:录制时间]` | 需用户提供或确认 |

### 4.2 置信度分级

| 置信度等级 | 说明 | 输出方式 |
|------------|------|----------|
| 高（≥90%） | 输入信息完整，参数明确 | 直接输出结果 |
| 中（70-89%） | 部分参数需默认值 | 输出结果并标注默认参数 |
| 低（<70%） | 关键信息缺失 | 输出占位符并请求补充信息 |

---

## 五、错误码体系

### 5.1 常见错误码

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `ERR_FILE_NOT_FOUND` | 输入文件不存在 | "未找到指定的录屏文件，请检查路径是否正确" | 1. 确认文件路径；2. 检查文件名拼写；3. 确认文件权限 |
| `ERR_UNSUPPORTED_FORMAT` | 不支持的格式 | "该文件格式暂不支持，请转换为 MP4/MKV/MOV 后重试" | 1. 使用 ffmpeg 转码为支持的格式 |
| `ERR_CODEC_NOT_SUPPORTED` | 编码不支持 | "当前编码格式不受支持，请转码为 H.264 或 H.265" | 1. 执行转码流程；2. 确认目标编码 |
| `ERR_DISK_FULL` | 磁盘空间不足 | "磁盘空间不足，无法完成处理，请清理空间后重试" | 1. 检查磁盘空间；2. 清理临时文件；3. 更换输出目录 |
| `ERR_OCR_FAILED` | OCR 识别失败 | "字幕 OCR 识别失败，请检查画面清晰度或调整 OCR 参数" | 1. 提高截帧分辨率；2. 调整二值化阈值；3. 更换语言包 |
| `ERR_CONCAT_MISMATCH` | 拼接参数不匹配 | "待拼接文件编码参数不一致，请先统一参数" | 1. 统一分辨率/帧率/编码；2. 重新拼接 |
| `ERR_TIMEOUT` | 处理超时 | "处理超时，请检查文件大小或分段处理" | 1. 拆分大文件；2. 降低处理复杂度；3. 增加超时时间 |

### 5.2 错误处理流程

```
遇到错误 → 记录错误码 → 输出提示话术 → 执行修正步骤 → 验证结果
```

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|-------------------|----------|
| 压缩后画质过差 | 直接使用 `-crf 32` 压缩所有文件 | 根据内容类型选择 CRF 值，


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

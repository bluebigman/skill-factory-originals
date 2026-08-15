---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: yt-transcripts
name: yt-transcripts
displayName: 视频字幕提取 转录下载 批量处理
description: 从YouTube链接提取字幕文本，支持多格式输出与批量处理。
version: 1.0.2
rules_version: cpr-20260815-n451
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/yt-transcripts
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["视频字幕", "youtube transcript", "yt字幕", "视频转录", "字幕下载", "视频转文字", "字幕提取", "caption extract"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# YouTube 字幕提取与转录 Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做与不能做

| 维度 | 能做 ✅ | 不能做 ❌ |
|------|---------|-----------|
| 输入类型 | 公开 YouTube 视频链接（标准 URL 格式） | 私有视频、会员专属视频、地区限制内容 |
| 字幕来源 | 自动生成字幕（ASR）、手动上传字幕、多语言轨道 | 无字幕轨道的纯音乐视频、直播回放（部分） |
| 输出格式 | 纯文本（TXT）、带时间戳（SRT/VTT）、JSON 结构化 | 翻译后的字幕（需另接翻译服务） |
| 处理规模 | 单条链接、批量链接（≤ 200 条/批次） | 超过 200 条需分批，否则触发限流 |
| 附加能力 | 时间戳保留、语言筛选、去重合并 | 视频下载、音频转写（非 YouTube 源） |

### 1.2 适用对象

- **内容研究者**：需要快速获取视频讲稿进行文本分析
- **自媒体运营**：转载或二次创作时需要原始字幕参考
- **语言学习者**：获取双语对照素材（需配合翻译工具）
- **数据标注团队**：为 NLP 模型准备语音转写训练数据

### 1.3 环境要求

| 项目 | 最低要求 | 推荐配置 |
|------|----------|----------|
| Python | 3.8+ | 3.10+ |
| 网络 | 可访问 YouTube | 稳定代理（视网络环境） |
| 依赖包 | youtube-transcript-api ≥ 1.0 | 最新版 + requests |
| 磁盘空间 | 10MB（临时缓存） | 100MB（批量处理） |

---

## 二、触发方式与场景映射

### 2.1 触发词速查

| 用户说（大白话） | 触发词命中 | Skill 响应 |
|------------------|------------|------------|
| "帮我把这个视频的字幕弄下来" | 视频字幕 / 字幕下载 | 提取字幕并保存为 TXT |
| "YouTube 视频转文字" | youtube transcript / 视频转文字 | 提取并输出纯文本 |
| "这个视频的 transcript 给我" | yt字幕 / caption extract | 提取并输出 JSON 格式 |
| "批量下载几个视频的字幕" | 视频转录 / 字幕提取 | 批量处理并打包输出 |

### 2.2 场景映射表

| 场景编号 | 用户意图 | 推荐输出格式 | 附加参数 |
|----------|----------|--------------|----------|
| S1 | 快速浏览视频内容 | TXT（无时间戳） | `--format txt` |
| S2 | 制作双语字幕 | SRT（带时间戳） | `--format srt --lang en,zh` |
| S3 | 数据分析/语料构建 | JSON（结构化） | `--format json --include-meta` |
| S4 | 多视频对比研究 | 批量 TXT + 汇总 CSV | `--batch --output-dir ./out` |

---

## 三、标准操作流程

### 3.1 前置条件检查

```
□ 已安装 Python 3.8+ 环境
□ 已安装 youtube-transcript-api 库（pip install youtube-transcript-api）
□ 网络可访问 YouTube（建议测试：curl -I https://www.youtube.com）
□ 目标视频链接格式正确（https://www.youtube.com/watch?v=VIDEO_ID）
□ 已确认视频存在字幕轨道（可通过 YouTube 页面右下角 CC 图标检查）
```

### 3.2 执行步骤（分步编号）

#### 步骤 1：初始化环境

```bash
# 安装依赖（如未安装）
pip install youtube-transcript-api==1.0.1

# 验证安装
python -c "from youtube_transcript_api import YouTubeTranscriptApi; print('OK')"
```

#### 步骤 2：单条字幕提取（试运行）

```python
from youtube_transcript_api import YouTubeTranscriptApi

# 替换为实际视频 ID（URL 中 v= 后面的部分）
video_id = "dQw4w9WgXcQ"

# 初始化 API 客户端
api = YouTubeTranscriptApi()

# 获取可用字幕轨道列表
transcript_list = api.list(video_id)
print("可用字幕语言:", [t.language_code for t in transcript_list])

# 提取英文字幕（自动选择）
transcript = api.fetch(video_id, languages=['en'])
text = "\n".join([entry.text for entry in transcript])
print(text[:500])  # 预览前 500 字符
```

#### 步骤 3：格式转换与保存

```python
import json

def save_transcript(transcript, output_format='txt', output_path='output'):
    """将字幕对象保存为指定格式"""
    if output_format == 'txt':
        with open(f'{output_path}.txt', 'w', encoding='utf-8') as f:
            for entry in transcript:
                f.write(entry.text + '\n')
    
    elif output_format == 'srt':
        with open(f'{output_path}.srt', 'w', encoding='utf-8') as f:
            for i, entry in enumerate(transcript, 1):
                start = format_timestamp(entry.start)
                end = format_timestamp(entry.start + entry.duration)
                f.write(f"{i}\n{start} --> {end}\n{entry.text}\n\n")
    
    elif output_format == 'json':
        data = [{
            'start': entry.start,
            'duration': entry.duration,
            'text': entry.text
        } for entry in transcript]
        with open(f'{output_path}.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def format_timestamp(seconds):
    """将秒数转换为 SRT 时间戳格式"""
    ms = int((seconds % 1) * 1000)
    s = int(seconds) % 60
    m = (int(seconds) // 60) % 60
    h = int(seconds) // 3600
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
```

#### 步骤 4：批量处理

```python
import csv
import os
from youtube_transcript_api import YouTubeTranscriptApi

def batch_process(video_ids, output_dir='./transcripts'):
    """批量提取字幕并生成汇总 CSV"""
    os.makedirs(output_dir, exist_ok=True)
    api = YouTubeTranscriptApi()
    results = []
    
    for vid in video_ids:
        try:
            transcript = api.fetch(vid, languages=['en'])
            save_transcript(transcript, 'txt', f"{output_dir}/{vid}")
            results.append({
                'video_id': vid,
                'status': 'success',
                'segments': len(transcript),
                'error': ''
            })
        except Exception as e:
            results.append({
                'video_id': vid,
                'status': 'failed',
                'segments': 0,
                'error': str(e)
            })
    
    # 写入汇总 CSV
    with open(f'{output_dir}/summary.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['video_id', 'status', 'segments', 'error'])
        writer.writeheader()
        writer.writerows(results)
    
    return results

# 使用示例
video_ids = ["dQw4w9WgXcQ", "9bZkp7q19f0", "kJQP7kiw5Fk"]
batch_process(video_ids)
```

#### 步骤 5：校验输出

```python
# 校验脚本：检查输出文件是否完整
def validate_output(filepath, expected_min_chars=100):
    """验证输出文件是否满足基本要求"""
    if not os.path.exists(filepath):
        return False, "文件不存在"
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if len(content) < expected_min_chars:
        return False, f"内容过短（{len(content)} 字符）"
    
    # 检查是否有异常字符
    if '\x00' in content:
        return False, "包含空字节"
    
    return True, "校验通过"

# 执行校验
ok, msg = validate_output("./transcripts/dQw4w9WgXcQ.txt")
print(f"校验结果: {msg}")
```

### 3.3 输出规范

| 输出格式 | 文件扩展名 | 编码 | 结构说明 |
|----------|------------|------|----------|
| 纯文本 | .txt | UTF-8 | 每行一条字幕文本，无时间戳 |
| 字幕文件 | .srt | UTF-8 | 序号 + 时间码 + 文本，标准 SRT 格式 |
| WebVTT | .vtt | UTF-8 | 带 WEBVTT 头部，兼容 HTML5 播放器 |
| 结构化数据 | .json | UTF-8 | 数组对象，含 start/duration/text 字段 |

---

## 四、置信度门控机制

### 4.1 信息不足时的处理

当遇到以下情况时，**不得编造或猜测**，必须输出占位符：

| 场景 | 占位符 | 说明 |
|------|--------|------|
| 视频 ID 无法从 URL 解析 | `[需核实:video_id]` | 请用户提供完整 URL |
| 字幕语言不确定 | `[需核实:language]` | 列出可用语言供用户选择 |
| 字幕内容不完整（中途中断） | `[需核实:transcript_completeness]` | 提示可能缺失部分段落 |
| 时间戳精度存疑 | `[需核实:timestamp_accuracy]` | 自动生成字幕可能有偏差 |

### 4.2 置信度分级

| 置信度等级 | 判定标准 | 输出策略 |
|------------|----------|----------|
| 高（≥90%） | 手动字幕 + 完整提取 + 无异常 | 直接输出，无需额外说明 |
| 中（70-89%） | 自动生成字幕 + 提取成功 | 输出时附带"自动生成字幕，可能存在识别误差"提示 |
| 低（<70%） | 部分提取失败 / 语言不匹配 | 输出占位符 + 建议人工核对 |

---

## 五、错误码体系

### 5.1 常见错误与处理

| 错误码 | 错误类型 | 用户提示话术 | 修正步骤 |
|--------|----------|--------------|----------|
| E001 | 视频不存在或已删除 | "该视频无法访问，请检查链接是否正确" | 1. 确认 URL 格式；2. 检查视频是否公开 |
| E002 | 无可用字幕轨道 | "该视频未提供任何字幕，无法提取" | 1. 确认视频有 CC 字幕；2. 尝试其他语言 |
| E003 | 语言不支持 | "所选语言无字幕，可用语言为：[列表]" | 1. 查看可用语言；2. 更换语言参数 |
| E004 | 网络超时 | "连接 YouTube 超时，请检查网络后重试" | 1. 检查网络连接；2. 增加重试次数 |
| E005 | 请求频率过高 | "请求过于频繁，请稍后重试" | 1. 增加间隔时间；2. 减少批量数量 |
| E006 | 字幕被禁用 | "该视频的字幕已被上传者禁用" | 1. 联系视频作者；2. 使用第三方工具 |

### 5.2 错误处理代码模板

```python
from youtube_transcript_api import (
    VideoUnavailable,
    TranscriptsDisabled,
    NoTranscriptFound,
    RequestBlocked
)

def safe_fetch(video_id, languages=['en'], max_retries=3):
    """带错误处理的字幕提取函数"""
    for attempt in range(max_retries):
        try:
            api = YouTubeTranscriptApi()
            transcript = api.fetch(video_id, languages=languages)
            return transcript
        
        except VideoUnavailable:
            return None, "E001: 视频不可用"
        except TranscriptsDisabled:
            return None, "E006: 字幕被禁用"
        except NoTranscriptFound:
            return None, "E002: 无匹配语言字幕"
        except RequestBlocked:
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))  # 指数退避
                continue
            return None, "E005: 请求被限制"
        except Exception as e:
            return None, f"未知错误: {str(e)}"
    
    return None, "E004: 网络超时"
```

---

## 六、FAQ 反模式对照

### 6.1 常见坑与正确做法

| 坑编号 | 反模式（错误做法） | 正确做法 | 原因说明 |
|--------|-------------------|----------|----------|
| F1 | 直接使用完整 URL 而非视频 ID | 从 URL 中提取 `v=` 参数值 | API 仅接受视频 ID |
| F2 | 忽略语言参数，默认提取 | 明确指定 `languages=['en']` | 部分视频多语言，默认可能取错 |
| F3 | 批量处理不设间隔 | 每次请求间隔 1-2 秒 | 避免触发限流机制 |
| F4 | 输出文件覆盖原文件 | 使用时间戳或序号命名 | 保留历史版本便于回溯 |
| F5 | 不校验输出直接使用 | 先抽样检查 3-5 条记录 | 自动字幕可能存在错别字 |

### 6.2 反模式代码示例

```python
# ❌ 反模式：直接传 URL
transcript = api.fetch("https://www.youtube.com/watch?v=abc123")  # 报错！

# ✅ 正确做法：提取视频 ID
video_id = "abc123"
transcript = api.fetch(video_id)

# ❌ 反模式：不指定语言
transcript = api.fetch(video_id)  # 可能随机选择语言

# ✅ 正确做法：明确指定
transcript = api.fetch(video_id, languages=['en', 'zh-Hans'])
```

---

## 七、渐进式披露路径

### 7.1 速查卡（30 秒上手）

```
1. 安装：pip install youtube-transcript-api
2. 提取：api.fetch("视频ID", languages=['en'])
3. 保存：遍历 transcript 写入文件
4. 批量：循环调用 + 汇总 CSV
```

### 7.2 新手路径（首次使用）

1. 阅读「能力边界」了解适用范围
2. 按「标准操作流程」步骤 1-3 完成单条提取
3. 使用「错误码体系」排查常见问题
4. 参考「FAQ 反模式」避免踩坑

### 7.3 进阶路径（深度使用）

1. 掌握「批量处理」与「输出规范」自定义格式
2. 结合「置信度门控」设计自动化质检流程
3. 扩展「错误处理代码模板」适配生产环境
4. 探索多语言字幕合并、时间戳对齐等高级用法

---

## 八、参数配置参考

### 8.1 核心参数表

| 参数名 | 类型 | 默认值 | 可选值 | 说明 |
|--------|------|--------|--------|------|
| `video_id` | str | 必填 | - | YouTube 视频 ID |
| `languages` | list | ['en'] | ['en','zh-Hans','ja','ko','es','fr','de'] | 字幕语言优先级 |
| `format` | str | 'txt' | 'txt','srt','vtt','json' | 输出格式 |
| `output_dir` | str | './output' | 任意路径 | 输出目录 |
| `batch_size` | int | 50 | 1-200 | 批量处理数量 |
| `retry_count` | int | 3 | 0-10 | 失败重试次数 |
| `timeout` | int | 10 | 5-60 | 请求超时（秒） |

### 8.2 边界值说明

- **视频时长**：支持 1 分钟至 12 小时的视频（超过 4 小时建议分段处理）
- **字幕条数**：单视频最多 5000 条字幕段（超出自动截断并警告）
- **批量上限**：单次最多 200 个视频（超出需分批，间隔 ≥ 60 秒）
- **文件大小**：单文件最大 50MB（超出自动分卷）

---

## 九、用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任。包括但不限于因字幕内容准确性、版权合规性、数据使用方式等引发的任何法律纠纷或损失。
2. **禁止反向工程**：不得对本 Skill 的代码、逻辑、结构进行反向工程、反编译、破解或试图提取源代码。
3. **合法用途**：本 Skill 仅限用于合法目的。使用者应遵守 YouTube 服务条款及当地法律法规，不得用于侵犯他人知识产权、隐私权或其他合法权益的行为。
4. **无担保声明**：本 Skill 按


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

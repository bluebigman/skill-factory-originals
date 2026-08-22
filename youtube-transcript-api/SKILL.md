---
slug: youtube-transcript-api
name: youtube-transcript-api
displayName: 视频字幕提取 转写文本获取
description: 获取YouTube视频字幕与转写文本的Python工具集。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 技术文档工作室
agent_created: true
trigger_words: ["视频字幕", "youtube-transcript-api", "字幕下载", "视频转写", "transcript", "字幕抓取", "视频文本提取"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# YouTube 字幕获取工具集（youtube-transcript-api）

## 一、能力边界速查卡

### 能做什么

| 能力项 | 说明 | 限制条件 |
|--------|------|----------|
| 获取字幕轨道 | 拉取指定视频的可用字幕轨道列表 | 仅限公开或未列出视频 |
| 下载字幕文本 | 获取纯文本格式的字幕内容 | 需视频存在字幕轨道 |
| 获取带时间戳字幕 | 输出包含时间码的字幕片段 | 需原始字幕含时间信息 |
| 多语言字幕支持 | 可按语言代码筛选字幕轨道 | 取决于视频上传者提供的语言 |
| 自动生成字幕获取 | 可获取YouTube自动生成的字幕 | 需视频已生成自动字幕 |

### 不能做什么

| 限制项 | 说明 |
|--------|------|
| 私有视频访问 | 无法获取私有或会员专属视频内容 |
| 年龄限制内容 | 无法获取需登录验证的视频字幕 |
| 实时直播流 | 不支持直播中的实时字幕获取 |
| 字幕翻译 | 仅获取原始字幕，不提供翻译功能 |
| 音频转写 | 不包含语音识别能力，仅获取已有字幕 |

### 适用对象

- 需要批量整理视频字幕内容的研究人员
- 需要提取视频文本用于内容分析的开发者
- 需要将视频内容转为文字稿的媒体从业者
- 需要建立视频文本索引的内容管理者

## 二、触发方式与场景映射

| 触发词 | 使用场景 | 具体操作 |
|--------|----------|----------|
| 视频字幕 | 需要获取某视频的字幕内容 | 调用工具获取指定视频字幕 |
| youtube-transcript-api | 明确使用该工具库 | 按文档调用API接口 |
| 字幕下载 | 需要将字幕保存为文件 | 执行下载并存储操作 |
| 视频转写 | 需要视频的文字版本 | 获取完整转写文本 |
| transcript | 英文场景下的字幕获取 | 使用英文参数调用 |
| 字幕抓取 | 批量获取多个视频字幕 | 编写循环脚本批量处理 |
| 视频文本提取 | 需要视频中的文字内容 | 提取并格式化输出 |

## 三、标准操作流程

### 前置条件

1. 确认目标视频可公开访问
2. 确认视频存在可用字幕轨道
3. 确认Python环境已安装所需依赖
4. 确认网络可正常访问YouTube服务

### 执行步骤

**第一步：环境准备**

```bash
pip install youtube-transcript-api
```

**第二步：获取字幕轨道列表**

```python
from youtube_transcript_api import YouTubeTranscriptApi

# 使用视频ID获取可用字幕轨道
video_id = "视频ID"
transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

# 查看所有可用轨道
for transcript in transcript_list:
    print(f"语言: {transcript.language_code}, 自动生成: {transcript.is_generated}")
```

**第三步：获取指定字幕内容**

```python
# 获取手动生成的字幕
transcript = transcript_list.find_manually_created_transcript(['en'])
full_text = transcript.fetch()
for segment in full_text:
    print(f"[{segment['start']:.2f}s] {segment['text']}")

# 获取自动生成的字幕
auto_transcript = transcript_list.find_generated_transcript(['zh-Hans'])
auto_text = auto_transcript.fetch()
```

**第四步：批量处理多个视频**

```python
video_ids = ["视频ID1", "视频ID2", "视频ID3"]
for vid in video_ids:
    try:
        api = YouTubeTranscriptApi()
        transcript = api.fetch(vid, languages=['en', 'zh-Hans'])
        # 保存到文件
        with open(f"{vid}_transcript.txt", "w", encoding="utf-8") as f:
            for segment in transcript:
                f.write(f"[{segment['start']:.2f}s] {segment['text']}\n")
    except Exception as e:
        print(f"视频 {vid} 处理失败: {e}")
```

### 输出规范

| 输出类型 | 格式要求 | 示例 |
|----------|----------|------|
| 字幕片段 | 时间戳 + 文本 | `[12.34s] 欢迎观看本视频` |
| 完整文本 | 纯文本内容 | 所有字幕文本按顺序拼接 |
| 轨道信息 | 语言代码 + 类型 | `en (手动生成)` |
| 错误信息 | 异常类型 + 详情 | `NoTranscriptFound: 未找到可用字幕` |

## 四、置信度门控机制

当遇到以下情况时，使用占位符标记，不进行推测：

| 场景 | 处理方式 | 输出示例 |
|------|----------|----------|
| 字幕语言不确定 | 标记语言代码待确认 | `[需核实:language_code]` |
| 时间戳精度不足 | 标记时间信息待验证 | `[需核实:timestamp]` |
| 字幕内容不完整 | 标记缺失片段 | `[需核实:missing_segment]` |
| 视频ID有效性未知 | 标记ID待确认 | `[需核实:video_id]` |

## 五、错误码体系

| 错误码 | 错误类型 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 视频不存在 | 视频ID无效或视频已删除 | 检查视频ID是否正确，确认视频可访问 |
| E002 | 字幕不可用 | 该视频未提供字幕轨道 | 尝试其他语言，或检查自动字幕是否生成 |
| E003 | 网络超时 | 连接YouTube服务超时 | 检查网络连接，稍后重试 |
| E004 | 语言不支持 | 请求的语言代码不存在 | 查看可用语言列表，选择支持的语言 |
| E005 | 权限限制 | 视频受访问限制 | 确认视频为公开状态，检查地区限制 |
| E006 | 参数错误 | 传入参数格式不正确 | 核对参数类型和格式，参考文档示例 |

## 六、常见问题与反模式

### 反模式一：忽略字幕轨道检查

**错误做法**：直接获取字幕，不检查可用轨道。

```python
# 错误示例
transcript = YouTubeTranscriptApi().fetch(video_id)
```

**正确做法**：先获取轨道列表，确认存在后再获取内容。

```python
# 正确示例
transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
if transcript_list:
    transcript = transcript_list[0].fetch()
```

### 反模式二：硬编码语言代码

**错误做法**：假设所有视频都有英文字幕。

**正确做法**：动态检查可用语言，选择最优轨道。

### 反模式三：忽略异常处理

**错误做法**：不捕获异常，程序直接崩溃。

**正确做法**：使用try-except捕获所有可能的异常。

### 反模式四：批量处理无间隔

**错误做法**：连续快速请求大量视频，触发限流。

**正确做法**：添加适当延时，控制请求频率。

### 反模式五：不验证输出结果

**错误做法**：直接使用获取的字幕，不检查内容完整性。

**正确做法**：抽查输出内容，验证时间戳和文本准确性。

## 七、渐进式学习路径

### 新手入门（5分钟上手）

1. 安装库：`pip install youtube-transcript-api`
2. 获取单个视频字幕
3. 保存为文本文件
4. 理解基本输出格式

### 进阶应用（30分钟掌握）

1. 多语言字幕处理
2. 批量视频处理
3. 异常处理与重试机制
4. 自定义输出格式
5. 与其他工具集成

### 高级技巧（1小时精通）

1. 并发请求优化
2. 缓存机制实现
3. 字幕数据清洗
4. 时间轴对齐处理
5. 自定义字幕解析器

## 八、实用参数参考

### 常用参数表

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| video_id | string | YouTube视频ID | "dQw4w9WgXcQ" |
| languages | list | 语言代码列表 | ['en', 'zh-Hans'] |
| preserve_formatting | bool | 保留原始格式 | True |
| proxies | dict | 代理设置 | {'http': '...'} |

### 语言代码速查

| 语言 | 代码 |
|------|------|
| 英语 | en |
| 简体中文 | zh-Hans |
| 繁体中文 | zh-Hant |
| 日语 | ja |
| 韩语 | ko |
| 西班牙语 | es |

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。本 Skill 仅提供技术指导，不构成任何形式的保证或承诺。

2. **合规使用**：使用者应确保其使用行为符合 YouTube 服务条款及相关法律法规。不得将本 Skill 用于侵犯他人版权、隐私或其他合法权益的活动。

3. **禁止反向工程**：使用者不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。

4. **免责声明**：本 Skill 按"现状"提供，不附带任何明示或暗示的保证。使用者应自行验证输出结果的准确性和适用性。

5. **服务变更**：YouTube 服务可能随时变更，导致本 Skill 描述的功能失效，使用者应自行关注并适应变化。

<!-- user-agreement-injected -->

## 许可证（License）

MIT License

Copyright (c) 2024 技术文档工作室

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

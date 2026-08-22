---
slug: serverless-subtitles
name: serverless-subtitles
displayName: 字幕转录 翻译 批处理工作流
description: 将字幕文件、转录文本或媒体链接，按规范流程处理为结构化结果。
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
trigger_words: ["serverless-subtitles", "字幕转录", "字幕翻译", "字幕处理", "批量字幕", "subtitle batch"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# serverless-subtitles 技能文档

本 Skill 由 AI 辅助生成，仅供参考。使用前请自行判断适用性。

## 一、能力边界速查卡

本技能用于处理字幕、转录文本及媒体链接，将其转换为结构化、可复用的结果。以下内容帮助你快速判断本技能是否适合你的场景。

### 能做（核心能力）

| 编号 | 能力项 | 说明 | 输入示例 |
|------|--------|------|----------|
| 1 | 字幕/转录文件结构化 | 将 SRT、VTT、TXT 等文件解析为带时间轴或段落标记的结构化数据 | `meeting.srt` |
| 2 | 媒体链接内容提取 | 从公开媒体 URL 中提取可用的转录文本或字幕轨道 | `https://example.com/video.mp4` |
| 3 | 关键信息识别与保留 | 自动识别说话人、语言、时间码、专有名词等关键字段并保留 | 多说话人对话转录 |
| 4 | 批量处理与格式转换 | 支持多文件批量处理，输出 JSON、CSV、Markdown 等自定义格式 | 文件夹内 50 个 `.vtt` 文件 |
| 5 | 置信度标注与人工复核辅助 | 对自动识别或翻译的内容标注置信度，便于后续人工校对 | 低置信度片段标记 `[需核实:时间码]` |

### 不能做（边界声明）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 不提供云端存储或部署服务 | 本技能仅处理本地输入，不涉及任何云端资源调用 |
| 2 | 不执行自动翻译 | 翻译功能需用户提供翻译引擎 API 或预先配置的术语库 |
| 3 | 不处理加密或 DRM 保护的媒体 | 仅支持公开可访问的媒体链接或本地文件 |
| 4 | 不保证识别准确率 | 自动语音识别的准确性受音质、口音、背景噪音影响，需人工复核 |
| 5 | 不替代专业字幕软件 | 本技能定位为批处理与格式转换工具，不提供实时预览或精细时间轴编辑 |

### 适用对象

- 需要批量整理字幕文件的视频创作者
- 需要将会议录音转为文字记录的项目助理
- 需要将字幕从一种格式转为另一种格式的开发者
- 需要为字幕添加翻译或术语标注的本地化团队

---

## 二、触发方式与场景映射

当你的请求中包含以下关键词或场景时，本技能将被触发：

| 触发词/场景 | 用户可能说的话（大白话示例） | 本技能响应 |
|-------------|------------------------------|------------|
| 字幕转录 | “帮我把这个会议录音转成文字” | 解析音频文件，输出带时间戳的转录文本 |
| 字幕翻译 | “这个英文字幕能翻成中文吗” | 调用用户配置的翻译接口，输出双语对照 |
| 字幕处理 | “把 SRT 转成 VTT 格式” | 格式转换，保留时间轴与文本内容 |
| 批量字幕 | “我有一整个文件夹的字幕要处理” | 批量解析，输出统一格式的结构化文件 |
| serverless-subtitles | “用 serverless-subtitles 处理一下” | 直接触发本技能的标准流程 |

---

## 三、标准处理流程

### 前置条件

在开始处理前，请确认以下条件已满足：

| 条件项 | 要求 | 检查方式 |
|--------|------|----------|
| 输入文件 | 文件格式为 `.srt`、`.vtt`、`.txt`、`.json` 或公开媒体 URL | 使用 `file` 命令或直接查看扩展名 |
| 文件命名 | 文件名需包含语言或内容标识，如 `meeting_en.srt` | 目视检查 |
| 依赖工具 | 如涉及翻译，需预先配置翻译 API 密钥 | 检查环境变量 `TRANSLATE_API_KEY` |
| 磁盘空间 | 至少保留输入文件 2 倍大小的可用空间 | 使用 `df -h` 查看 |

### 执行步骤

#### 第 1 步：准备输入

将待处理的字幕文件或转录文本放入同一工作目录。确认命名规范一致，例如：

```
./input/
├── episode01_en.srt
├── episode01_zh.srt
└── episode02_en.vtt
```

#### 第 2 步：试运行（单样本验证）

使用单个文件执行一次处理，核对输出字段与格式是否符合预期：

```bash
# 示例命令（伪代码）
process-subtitles --input ./input/episode01_en.srt --output ./output/episode01.json
```

检查输出 JSON 是否包含以下字段：

```json
{
  "source_file": "episode01_en.srt",
  "language": "en",
  "segments": [
    {
      "start": "00:00:01,000",
      "end": "00:00:04,000",
      "text": "Hello world",
      "confidence": 0.95
    }
  ]
}
```

#### 第 3 步：批量执行

确认单样本无误后，对全量数据执行处理：

```bash
process-subtitles --input ./input/ --output ./output/ --format json
```

**重要**：执行前务必备份原始文件。建议使用 `cp -r input input_backup` 保留副本。

#### 第 4 步：校验结果

抽查输出条目，核对关键字段与源数据的一致性：

| 校验项 | 方法 | 通过标准 |
|--------|------|----------|
| 时间轴完整性 | 对比源文件与输出文件的时间码 | 无缺失或跳变 |
| 文本一致性 | 随机抽取 5 条对比原文 | 文本内容一致（除格式转换外） |
| 置信度标注 | 检查低置信度条目是否被标记 | 所有 `confidence < 0.7` 的条目均有 `[需核实]` 标记 |

### 输出规范

本技能默认输出 JSON 格式，字段结构如下：

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `source_file` | string | 是 | 源文件名 |
| `language` | string | 是 | 语言代码（ISO 639-1） |
| `segments` | array | 是 | 字幕段数组 |
| `segments[].start` | string | 是 | 开始时间码 |
| `segments[].end` | string | 是 | 结束时间码 |
| `segments[].text` | string | 是 | 字幕文本 |
| `segments[].confidence` | number | 否 | 置信度（0-1），缺失时默认 0.5 |
| `segments[].speaker` | string | 否 | 说话人标识（如适用） |

---

## 四、置信度门控机制

当处理过程中出现信息不足或不确定的情况时，本技能遵循以下原则：

### 信息不足时的处理

| 场景 | 处理方式 | 输出示例 |
|------|----------|----------|
| 无法识别说话人 | 在 `speaker` 字段输出 `[需核实:说话人]` | `"speaker": "[需核实:说话人]"` |
| 时间码缺失 | 在 `start`/`end` 字段输出 `[需核实:时间码]` | `"start": "[需核实:时间码]"` |
| 翻译结果不确定 | 在 `text` 字段追加 `[需核实:翻译]` | `"text": "Hello world [需核实:翻译]"` |
| 语言识别不确定 | 在 `language` 字段输出 `[需核实:语言]` | `"language": "[需核实:语言]"` |

### 禁止行为

- **严禁编造数据**：当无法从输入中获取信息时，不得自行推测填充。
- **严禁静默忽略**：所有不确定项必须显式标注，不得直接省略。

---

## 五、错误码体系

本技能定义了以下错误码，用于统一错误提示与修正指引：

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入文件不存在 | “未找到指定的输入文件，请检查路径是否正确。” | 1. 使用 `ls` 确认文件路径；2. 修正路径后重试 |
| `E002` | 文件格式不支持 | “当前文件格式不在支持列表中（srt/vtt/txt/json/URL）。” | 1. 转换文件格式；2. 或提供支持的格式 |
| `E003` | 翻译 API 未配置 | “检测到需要翻译，但未找到翻译 API 密钥。” | 1. 设置环境变量 `TRANSLATE_API_KEY`；2. 或跳过翻译步骤 |
| `E004` | 批量处理中断 | “批量处理在第 N 个文件处中断，请检查该文件。” | 1. 定位中断文件；2. 单独处理该文件排查问题 |
| `E005` | 输出目录不可写 | “无法写入输出目录，请检查权限。” | 1. 使用 `chmod` 修改目录权限；2. 或更换输出目录 |
| `E006` | 置信度低于阈值 | “检测到大量低置信度条目，建议人工复核。” | 1. 导出低置信度清单；2. 安排人工校对 |

---

## 六、常见坑与反模式对照（FAQ）

以下列举使用本技能时常见的错误操作及正确的处理方式：

| 反模式（错误做法） | 问题说明 | 正确做法（正模式） |
|--------------------|----------|---------------------|
| 直接批量处理所有文件，不做试运行 | 格式错误会放大到所有文件，返工成本高 | 先处理单个文件验证格式，再批量执行 |
| 覆盖原始文件，不保留备份 | 处理出错后无法恢复原始数据 | 始终保留 `input_backup` 目录 |
| 忽略置信度标注，直接使用结果 | 低质量片段混入最终输出，影响交付质量 | 对 `confidence < 0.7` 的条目进行人工复核 |
| 在文件名中使用特殊字符或空格 | 解析时可能产生意外错误 | 使用下划线或连字符命名，如 `meeting_2024_01.srt` |
| 将翻译结果直接用于发布 | 自动翻译可能存在语义偏差 | 翻译后必须经母语者校对再发布 |

---

## 七、渐进式阅读路径

本技能文档信息量较大，建议根据你的经验水平选择阅读路径：

### 新手路径（首次使用）

1. **必读**：第一部分「能力边界速查卡」——了解本技能能做什么、不能做什么。
2. **必读**：第三部分「标准处理流程」——按步骤操作，先跑通单样本。
3. **参考**：第四部分「置信度门控机制」——理解输出中的 `[需核实]` 标记含义。

### 进阶路径（熟练用户）

1. **必读**：第五部分「错误码体系」——遇到报错时快速定位问题。
2. **必读**：第六部分「常见坑与反模式对照」——避免重复踩坑。
3. **参考**：第三部分「输出规范」——自定义输出格式时对照字段定义。

### 专家路径（深度定制）

1. **必读**：全部章节，重点关注输出规范的字段扩展方式。
2. **实践**：修改处理流程中的参数（如置信度阈值、输出格式）以适应特定场景。
3. **扩展**：结合其他工具链，将本技能输出接入下游自动化流程。

---

## 八、用户协议

使用本技能即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本技能产生的全部责任。本技能仅供学习与参考用途，不构成任何形式的专业建议或服务承诺。
2. **禁止反向工程**：不得对本技能进行反向工程、反编译、破解或试图提取底层算法。
3. **合规使用**：使用者须确保输入数据的合法性与授权，不得处理侵犯他人版权、隐私或违反法律法规的内容。
4. **无担保声明**：本技能按“现状”提供，不附带任何明示或暗示的担保。

<!-- user-agreement-injected -->

---

## 九、许可证（License）

本项目采用 MIT 许可证授权。

### MIT License

```
MIT License

Copyright (c) 2024 原创作者（自持版权）

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

*文档版本：1.0.0 | 最后更新：2024 年*

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: automate-download-freesound
name: automate-download-freesound
displayName: 音频批量采集 自动化下载 资源整理
description: 自动化批量下载Freesound音频文件，支持筛选、重试与结构化归档。
version: 1.0.1
rules_version: cpr-20260809-n251
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/automate-download-freesound
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["freesound", "download", "audio", "批量下载", "声音素材", "音效采集"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 音频批量采集 Skill 使用指南

## 一、能力边界（一页纸速查卡）

### 能做（核心能力）

| 编号 | 能力项 | 说明 |
|------|--------|------|
| 1 | 批量下载 | 根据用户提供的 Freesound 页面 URL 或搜索关键词，批量下载音频文件 |
| 2 | 元数据提取 | 自动提取音频的标题、作者、标签、时长、采样率等元数据 |
| 3 | | 支持将下载的音频统一转换为指定格式（如 MP3、WAV） |
| 4 | 结构化归档 | 按预设规则（如标签、时长、评分）对下载文件进行分类归档 |
| 5 | 断点续传 | 支持中断后重新执行，已下载文件自动跳过，避免重复下载 |

### 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| 1 | 绕过版权保护 | 不提供任何绕过 Freesound 版权限制或授权协议的功能 |
| 2 | 非公开内容下载 | 无法下载需要特殊权限或非公开的音频资源 |
| 3 | 无限并发 | 不提供无节制的并发下载，默认并发数上限为 5，防止对目标服务器造成压力 |
| 4 | 音频内容分析 | 不提供音频内容识别、转写、情感分析等后续处理能力 |
| 5 | 实时流媒体录制 | 不支持对实时音频流进行录制或抓取 |

### 适用对象

- 需要批量获取音效素材的音频创作者
- 需要建立本地声音素材库的开发者
- 需要离线使用 Freesound 音频资源的研究人员

---

## 二、触发方式

### 触发词

当用户输入包含以下关键词时，本 Skill 将被激活：

- `freesound`、`下载音频`、`批量下载`、`声音素材`、`音效采集`、`audio download`

### 场景映射表

| 用户场景 | 触发示例 | 本 Skill 响应 |
|----------|----------|---------------|
| 批量获取特定标签的音效 | "帮我下载 Freesound 上所有标签为 rain 的音频" | 解析标签，生成下载任务列表 |
| 根据页面链接下载 | "把这个页面的音频都下载下来" | 提取页面内所有音频链接 |
| 按条件筛选下载 | "下载时长在 5 秒以内的水滴声" | 设置筛选条件，执行下载 |
| 需要特定格式 | "下载后转成 WAV 格式" | 下载后执行 |
| 中断后继续 | "上次没下完，继续" | 读取进度记录，跳过已完成项 |

---

## 三、标准工作流程

### 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| 网络连接 | 可访问 freesound.org | 执行 `curl -sI https://freesound.org` 验证 |
| Python 环境 | Python 3.8+ | 执行 `python --version` 验证 |
| 依赖包 | requests, beautifulsoup4, mutagen | 执行 `pip list` 检查 |
| 磁盘空间 | 至少 2 倍于待下载文件总大小 | 执行 `df -h` 检查 |

### 执行步骤

1. **输入解析**：收集用户提供的 URL、关键词或文件列表，解析为结构化任务描述
2. **任务规划**：根据输入生成下载任务清单，包含每个文件的 URL、预期文件名、保存路径
3. **预检**：检查网络连通性、目标页面可访问性、磁盘空间
4. **执行下载**：按任务清单逐个下载，每下载一个文件后立即校验文件完整性
5. **元数据记录**：下载完成后，为每个文件生成对应的 `.json` 元数据文件
6. **格式处理**：如用户指定，调用 ffmpeg 执行转换
7. **归档整理**：按预设规则将文件移动到对应分类目录
8. **生成报告**：输出下载结果汇总，包括成功/失败/跳过的文件清单

### 输出规范

下载完成后，输出以下内容：

```
下载完成报告
============
成功：45 个文件（总计 128.5 MB）
失败：3 个文件（详见失败清单）
跳过：2 个文件（已存在）

保存路径：/downloads/freesound_20260809/
元数据：/downloads/freesound_20260809/metadata/
```

---

## 四、置信度门控

### 信息不足时的处理

当输入信息不足以生成明确的下载任务时，使用以下占位符标记：

| 场景 | 占位符 | 示例 |
|------|--------|------|
| 缺少搜索关键词 | `[需核实:搜索关键词]` | "请提供要搜索的音频关键词" |
| 缺少保存路径 | `[需核实:保存路径]` | "请指定文件保存目录" |
| 缺少筛选条件 | `[需核实:筛选条件]` | "是否需要按时长、评分等条件筛选？" |
| 链接无法访问 | `[需核实:链接有效性]` | "该链接返回 404，请确认链接是否正确" |

### 禁止行为

- 不得在信息不足时猜测用户意图并执行下载
- 不得编造不存在的文件或下载结果
- 不得在未确认的情况下覆盖已有文件

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 网络连接失败 | "无法连接到 freesound.org，请检查网络设置" | 1. 检查网络连接；2. 确认防火墙未屏蔽；3. 重试 |
| E002 | 页面解析失败 | "无法解析目标页面，可能页面结构已变更" | 1. 确认 URL 正确；2. 尝试使用搜索关键词替代；3. 反馈给维护者 |
| E003 | 文件下载不完整 | "文件大小与预期不符，下载可能中断" | 1. 删除不完整文件；2. 重新下载该文件 |
| E004 | 磁盘空间不足 | "磁盘剩余空间不足，无法继续下载" | 1. 清理磁盘；2. 更换保存路径；3. 减少下载数量 |
| E005 | 失败 | "ffmpeg 转换失败，请检查源文件完整性" | 1. 确认 ffmpeg 已安装；2. 检查源文件；3. 跳过转换直接保存原格式 |
| E006 | 权限不足 | "没有写入目标目录的权限" | 1. 更换目录；2. 修改目录权限；3. 以管理员身份运行 |

---

## 六、FAQ 反模式对照

### 常见坑与正确做法

| 常见错误 | 反模式 | 正确做法 |
|----------|--------|----------|
| 下载所有搜索结果 | 不加筛选直接下载全部结果，导致大量无关文件 | 先预览搜索结果，确认符合预期后再批量下载 |
| 忽略文件命名冲突 | 不同页面可能存在同名文件，直接覆盖 | 在文件名后追加哈希值或序号，确保唯一性 |
| 并发数过高 | 设置 20+ 并发下载，导致服务器拒绝服务 | 保持默认并发数 5，必要时逐步调高 |
| 不校验文件完整性 | 下载完成后不检查文件大小，导致损坏文件混入 | 每个文件下载后立即比对 Content-Length |
| 忽略元数据 | 只下载音频文件，不保存元数据信息 | 为每个文件生成配套的 `.json` 元数据文件 |

---

## 七、渐进式披露

### 速查卡（新手快速上手）

```
1. 提供关键词或链接
2. 确认下载条件
3. 等待下载完成
4. 查看报告
```

### 新手路径（首次使用）

1. 阅读「能力边界」了解本 Skill 能做什么
2. 阅读「触发方式」了解如何发起请求
3. 按「标准工作流程」执行一次完整下载
4. 遇到问题查阅「错误码体系」

### 进阶路径（熟练用户）

1. 自定义归档规则（修改配置文件中的分类逻辑）
2. 调整并发参数（在配置文件中修改 `max_concurrency`）
3. 编写自定义后处理脚本（在下载完成后自动执行）
4. 集成到 CI/CD 流水线（通过命令行接口调用）

---

## 八、命令行接口

### 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `--selftest` | 运行自检，验证环境配置 | `python main.py --selftest` |
| `--version` | 显示版本信息 | `python main.py --version` |

### 自检输出示例

```
环境检查：
 Python 版本：3.10.12 ✓
 依赖包：requests ✓ / beautifulsoup4 ✓ / mutagen ✓
 网络连接：freesound.org 可达 ✓
 磁盘空间：剩余 12.5 GB ✓
 配置检查：配置文件有效 ✓
所有检查通过，可以正常使用。
```

---

## 九、配置参数参考

| 参数名 | 默认值 | 说明 | 取值范围 |
|--------|--------|------|----------|
| `max_concurrency` | 5 | 最大并发下载数 | 1-10 |
| `timeout` | 30 | 单次请求超时时间（秒） | 10-120 |
| `retry_count` | 3 | 失败重试次数 | 0-5 |
| `output_dir` | `./downloads` | 默认保存目录 | 任意有效路径 |
| `file_format` | `original` | 输出格式 | `original` / `mp3` / `wav` |
| `save_metadata` | `true` | 是否保存元数据 | `true` / `false` |

---

## 用户协议

<!-- user-agreement-injected -->

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担使用本 Skill 的全部责任。因使用本 Skill 导致的任何直接或间接损失，包括但不限于数据丢失、系统故障、法律纠纷，本 Skill 作者不承担任何责任。
2. **合法使用**：使用者承诺仅将本 Skill 用于合法目的，遵守 Freesound 网站的服务条款及相关法律法规。
3. **禁止反向工程**：使用者不得对本 Skill 进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。
4. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。
5. **内容合规**：使用者下载的音频内容仅限用于合法用途，不得侵犯任何第三方的知识产权。

---

## 许可证（License）

<!-- professional-license-embedded -->

MIT License

Copyright (c) 2026 LinguaForge

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

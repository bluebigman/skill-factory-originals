---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: awesome-mac
name: awesome-mac
displayName: macOS 精品软件 分类整理 检索速查
description: 将 macOS 优质软件按类别系统整理，支持检索与结构化输出。
version: 1.0.1
rules_version: cpr-20260809-n251
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/awesome-mac
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: mac-curator
agent_created: true
trigger_words: ["awesome-mac", "macOS 软件推荐", "Mac 应用整理", "mac 软件清单", "macOS 工具汇总"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


# awesome-mac — macOS 精品软件分类整理与检索 Skill

## 一、能力边界（一页纸速查卡）

### 1.1 能做（核心能力）

| 编号 | 能力项 | 说明 | 示例 |
|------|--------|------|------|
| C1 | 数据/文件/URL 解析 | 从用户提供的文本、文件路径或网页链接中提取软件名称、类别、描述等关键信息 | 用户粘贴一个 GitHub 链接，提取其中列出的软件名与分类 |
| C2 | 关键信息识别与保留 | 自动识别软件名称、版本、适用场景、评分、开源/付费等属性，并保留原始上下文 | 从一段评测文章中提取「CleanMyMac X — 系统清理 — 付费」 |
| C3 | 结构化输出 | 按约定的 Markdown 表格、JSON 或分层列表格式输出整理结果 | 输出「按类别分组的软件清单表」 |
| C4 | 置信度标注 | 对不确定的字段（如软件是否免费、是否仍在维护）标注 `[需核实:字段名]` | `[需核实:是否免费]` |
| C5 | 批量处理与自定义格式 | 支持一次处理多条记录，并允许用户指定输出字段与排序方式 | 用户要求「只输出开源软件，按星标数降序」 |

### 1.2 不能做（明确边界）

| 编号 | 限制项 | 说明 |
|------|--------|------|
| L1 | 不编造软件信息 | 若输入中未提供某软件的价格、评分等，不自行猜测，必须标注 `[需核实]` |
| L2 | 不提供下载链接 | 仅整理与分类，不生成任何下载地址或破解资源 |
| L3 | 不评价软件优劣 | 只做客观分类与属性提取，不做「最好用」「强烈推荐」等主观评价 |
| L4 | 不处理非 macOS 软件 | 仅针对 macOS 平台的应用与工具，其他平台内容需明确提示用户 |

### 1.3 适用对象

- 需要整理 macOS 软件清单的个人用户
- 撰写技术博客或软件推荐帖的内容创作者
- 需要在团队内共享软件选型列表的运维或 IT 管理员

---

## 二、触发方式

### 2.1 触发词

- 直接触发：`awesome-mac`、`macOS 软件推荐`、`Mac 应用整理`
- 同义触发：`mac 软件清单`、`macOS 工具汇总`、`Mac 应用列表`

### 2.2 场景映射表

| 用户实际说（大白话） | 触发动作 |
|---------------------|----------|
| 「帮我把这个网页里的 Mac 软件整理一下」 | 解析 URL，提取软件列表，按类别输出 |
| 「我有一堆软件名，帮我分个类」 | 接收文本列表，按功能分类整理 |
| 「把这份 CSV 里的软件信息转成表格」 | 解析 CSV，映射字段，输出 Markdown 表格 |
| 「只保留开源的，按更新时间排序」 | 应用过滤条件，自定义排序输出 |
| 「这个软件是不是免费我不确定」 | 保留原信息，标注 `[需核实:是否免费]` |

---

## 三、标准流程

### 3.1 前置条件

- 用户需提供至少一个输入来源：文本、文件路径或 URL
- 若输入为空，则返回错误码 `E1001` 并提示正确格式

### 3.2 执行步骤

| 步骤 | 操作 | 详细说明 |
|------|------|----------|
| 1 | 收集输入并确认格式 | 询问用户输入类型（文本/文件/URL），确认输出格式偏好（默认 Markdown 表格） |
| 2 | 解析输入内容 | 提取软件名称、类别、描述、开源/付费、星标数、更新时间等字段 |
| 3 | 按规则处理 | ① 类别映射：将原始分类归入标准类别（见 3.4 类别表）；② 去重：同名软件合并；③ 过滤：按用户条件筛选 |
| 4 | 生成结果并标注置信度 | 对缺失或不确定字段标注 `[需核实:字段名]` |
| 5 | 自查与输出 | 检查字段完整性、格式正确性，输出最终结果 |

### 3.3 输出规范

- **默认格式**：Markdown 表格，列为 `软件名称 | 类别 | 描述 | 开源/付费 | 备注`
- **自定义格式**：用户可指定 JSON、CSV 或纯文本列表
- **排序规则**：默认按类别分组，组内按名称字母序；用户可指定按星标数、更新时间等排序

### 3.4 标准类别表

| 类别 ID | 类别名称 | 包含示例 |
|---------|----------|----------|
| CAT_DEV | 开发工具 | 编辑器、IDE、版本控制客户端 |
| CAT_SYS | 系统增强 | 清理工具、窗口管理、系统监控 |
| CAT_NET | 网络与通信 | 浏览器、下载工具、远程连接 |
| CAT_MEDIA | 媒体处理 | 图片编辑、视频播放、音频处理 |
| CAT_PROD | 生产力 | 笔记、日历、任务管理 |
| CAT_SEC | 安全与隐私 | 密码管理、防火墙、加密工具 |
| CAT_OTHER | 其他 | 无法归入以上类别的工具 |

---

## 四、置信度门控

### 4.1 规则说明

- 当输入中缺少某字段信息时，**不得**自行推断或编造，必须输出 `[需核实:字段名]`
- 当输入中信息存在矛盾（如同一软件既标免费又标付费），输出 `[需核实:价格]` 并保留两条原始信息供用户确认

### 4.2 示例

**输入**：`iTerm2 — 终端工具`

**输出**：

| 软件名称 | 类别 | 描述 | 开源/付费 | 备注 |
|----------|------|------|-----------|------|
| iTerm2 | CAT_DEV | 终端工具 | [需核实:是否开源] | [需核实:最新版本] |

---

## 五、错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E1001 | 输入为空 | 「未检测到输入内容。请提供文本、文件路径或 URL。」 | 用户提供至少一条输入 |
| E1002 | 输入格式无法解析 | 「无法从输入中提取有效信息。请确认内容与 macOS 软件相关。」 | 检查输入内容，重新提交 |
| E1003 | 文件不存在或无法访问 | 「指定的文件路径不存在或无法读取。请确认路径正确。」 | 检查路径，重新提交 |
| E1004 | URL 无法访问 | 「无法访问该 URL，可能已失效或需要网络权限。」 | 检查链接有效性，或改为粘贴文本 |
| E1005 | 类别映射失败 | 「存在无法归类的软件，已放入『其他』类别。」 | 用户可手动指定类别，或接受默认归类 |

---

## 六、FAQ 与反模式

### 6.1 常见坑

| 坑编号 | 坑描述 | 反模式（错误做法） | 正确做法 |
|--------|--------|-------------------|----------|
| F1 | 编造缺失字段 | 软件未标注价格，自行猜测「免费」 | 标注 `[需核实:是否免费]` |
| F2 | 忽略去重 | 同一软件出现多次，重复列出 | 按名称去重，合并信息 |
| F3 | 类别混乱 | 将「终端工具」归入「媒体处理」 | 严格按 3.4 类别表映射 |
| F4 | 输出格式不统一 | 有时输出表格，有时输出列表 | 默认表格，用户指定才变更 |
| F5 | 主观评价 | 输出「这款软件非常好用」 | 仅输出客观属性，不做评价 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 「这个软件是最好的」 | 绝对化用语，违反合规 | 「该软件在 XX 场景下使用较多」 |
| 「我保证这个软件免费」 | 信息不确定却打包票 | 「根据输入信息标注为免费，[需核实]」 |
| 「所有 Mac 用户都需要它」 | 过度推广 | 「该软件适用于需要 XX 功能的用户」 |

---

## 七、渐进式披露

### 7.1 速查卡（新手路径）

1. 输入你的软件列表或链接
2. 确认输出格式（默认表格）
3. 获取分类整理结果
4. 对不确定项自行核实

### 7.2 进阶路径（熟练用户）

- 使用自定义过滤条件：`只保留开源`、`按星标数排序`
- 指定输出格式：`输出 JSON`、`输出 CSV`
- 批量处理：一次粘贴 50 条以上软件信息
- 自定义类别：提供自己的分类规则覆盖默认类别表

### 7.3 参数表

| 参数名 | 类型 | 默认值 | 可选值 | 说明 |
|--------|------|--------|--------|------|
| `format` | string | `markdown` | `markdown` / `json` / `csv` | 输出格式 |
| `sort_by` | string | `name` | `name` / `stars` / `updated` | 排序字段 |
| `filter_open_source` | boolean | `false` | `true` / `false` | 是否只保留开源软件 |
| `category` | string | `all` | `CAT_DEV` / `CAT_SYS` 等 | 按类别过滤 |

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。本 Skill 仅提供信息整理与分类服务，不构成任何形式的软件推荐、购买建议或安全保证。
2. **信息准确性**：本 Skill 输出的所有信息均基于用户提供的输入内容。对于标注 `[需核实]` 的字段，使用者应自行验证其准确性。
3. **禁止反向工程**：使用者不得对本 Skill 的提示词、处理逻辑、内部结构进行反向工程、破解、提取或二次分发。
4. **合规使用**：使用者不得将本 Skill 用于任何违反法律法规或平台规定的用途。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

Copyright (c) 2026 原创作者（自持版权）

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*

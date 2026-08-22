---
slug: awesome-mac
name: awesome-mac
displayName: Mac应用精选 分类检索 软件清单
description: 将macOS优质软件按类别系统整理，支持检索与结构化输出。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: mac-curator
agent_created: true
trigger_words: ["awesome-mac", "macOS 软件推荐", "Mac 应用整理", "mac 软件清单", "macOS 工具汇总", "Mac 应用精选", "mac 软件分类", "Mac 效率工具"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# SKILL.md — awesome-mac

## 1. 能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 软件分类 | 将输入的软件名称映射到预定义类别 | "Alfred" → 效率工具 |
| 批量处理 | 同时处理多个软件名称（逗号/换行分隔） | "iStat Menus, Bartender, CleanMyMac X" |
| 信息标注 | 对无法确认的条目标注 `[需核实]` 占位符 | "某小众软件 → [需核实:类别]" |
| 格式输出 | 默认表格输出，支持 JSON 结构化输出 | 表格 / JSON 二选一 |
| 自定义映射 | 用户可提供关键词对照表覆盖默认规则 | "输入: 关键词表 + 软件列表" |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不提供下载链接 | 仅分类与整理，不涉及获取渠道 |
| 不评价软件质量 | 不输出"最好用""强烈推荐"等主观判断 |
| 不保证信息实时性 | 软件类别可能随版本更新变化，需自行验证 |
| 不处理非文本输入 | 不支持图片、音频、视频中的软件识别 |
| 不提供安装指导 | 不涉及安装步骤、配置教程 |

### 1.3 适用对象

- 需要整理 Mac 软件清单的个人用户
- 需要按类别归档软件列表的团队管理员
- 需要快速检索某类工具的开发者和设计师

---

## 2. 触发方式

### 2.1 触发词

以下任一词汇或短语出现时，本 Skill 自动激活：

- `awesome-mac`
- `macOS 软件推荐`
- `Mac 应用整理`
- `mac 软件清单`
- `macOS 工具汇总`
- `Mac 应用精选`
- `mac 软件分类`
- `Mac 效率工具`

### 2.2 场景映射表

| 用户说（大白话） | 实际意图 | 本 Skill 响应 |
|------------------|----------|---------------|
| "帮我整理一下这些 Mac 软件" | 对软件列表分类 | 执行分类流程，输出表格 |
| "有哪些好用的 Mac 效率工具？" | 检索某类软件 | 输出效率工具类别清单 |
| "这个列表里哪些是开发工具？" | 筛选特定类别 | 过滤并输出开发工具子集 |
| "把这份软件清单按类别分一下" | 批量分类 | 解析全部条目，映射类别 |
| "用 JSON 格式给我结果" | 结构化输出 | 切换为 JSON 输出模式 |

---

## 3. 标准流程

### 3.1 前置条件

- 输入内容为文本格式（支持纯文本、URL、混合格式）
- 输入中至少包含一个可识别的软件名称或链接
- 软件名称之间使用逗号、换行或分号分隔

### 3.2 执行步骤

#### 步骤 1：接收输入

读取用户提供的软件列表，支持以下分隔符：

| 分隔符 | 示例 |
|--------|------|
| 逗号 `,` | "Alfred, Bartender, iStat Menus" |
| 换行 `\n` | "Alfred\nBartender\niStat Menus" |
| 分号 `;` | "Alfred; Bartender; iStat Menus" |

#### 步骤 2：解析条目

- 去除首尾空白字符
- 去除多余标点（如句号、引号）
- 识别 URL 中的软件名（提取域名或路径中的关键词）
- 过滤空条目和无效字符

#### 步骤 3：类别映射

根据软件名称关键词或内置知识库，映射到以下类别之一：

| 类别 | 关键词示例 | 典型软件 |
|------|------------|----------|
| 效率工具 | 启动器、剪贴板、窗口管理 | Alfred, Raycast, Rectangle |
| 开发工具 | 编辑器、终端、版本控制 | VS Code, iTerm2, GitKraken |
| 系统工具 | 清理、监控、卸载 | CleanMyMac X, iStat Menus, AppCleaner |
| 设计工具 | 绘图、原型、截图 | Sketch, Figma, Snagit |
| 影音工具 | 播放器、转码、录制 | IINA, HandBrake, OBS Studio |
| 网络工具 | 浏览器、下载、代理 | Chrome, Downie, Surge |
| 办公软件 | 文档、表格、笔记 | Microsoft Office, Notion, Bear |
| 安全工具 | 杀毒、密码管理、防火墙 | Little Snitch, 1Password, Malwarebytes |
| 其他 | 无法归入以上类别 | [需核实:类别] |

#### 步骤 4：信息标注

- 无法确定类别的条目 → 标注 `[需核实:类别]`
- 名称疑似拼写错误的条目 → 标注 `[需核实:名称]`
- 名称存在多个同名软件的条目 → 标注 `[需核实:歧义]`

#### 步骤 5：输出结果

按用户选择的格式输出（默认表格）。

**表格格式示例：**

| 软件名称 | 类别 | 备注 |
|----------|------|------|
| Alfred | 效率工具 | — |
| VS Code | 开发工具 | — |
| 某小众软件 | [需核实:类别] | 未找到匹配 |

**JSON 格式示例：**

```json
{
  "items": [
    {"name": "Alfred", "category": "效率工具", "note": ""},
    {"name": "VS Code", "category": "开发工具", "note": ""},
    {"name": "某小众软件", "category": null, "note": "需核实:类别"}
  ]
}
```

### 3.3 输出规范

- 默认输出 Markdown 表格
- 表格包含三列：软件名称、类别、备注
- 所有 `[需核实]` 项必须在备注列明确标注
- JSON 输出时，`category` 字段为 `null` 表示需核实

---

## 4. 置信度门控

### 4.1 基本原则

**不编造。** 当信息不足或无法确认时，使用 `[需核实:字段]` 占位符，而非猜测或推断。

### 4.2 占位符规则

| 场景 | 占位符 | 示例 |
|------|--------|------|
| 无法确定类别 | `[需核实:类别]` | "某小众软件 → [需核实:类别]" |
| 名称可能拼写错误 | `[需核实:名称]` | "Alferd → [需核实:名称]" |
| 存在同名歧义 | `[需核实:歧义]` | "Telegram（有多个同名软件）→ [需核实:歧义]" |
| 版本信息不确定 | `[需核实:版本]` | "某软件最新版本 → [需核实:版本]" |

### 4.3 置信度分级

| 置信度 | 判定条件 | 输出方式 |
|--------|----------|----------|
| 高（≥90%） | 软件名称与内置知识库完全匹配 | 直接输出类别 |
| 中（70%-89%） | 名称部分匹配或关键词命中 | 输出类别并备注"基于关键词推断" |
| 低（<70%） | 无匹配或信息不足 | 输出 `[需核实:类别]` |

---

## 5. 错误码体系

| 错误码 | 错误描述 | 提示话术 | 修正步骤 |
|--------|----------|----------|----------|
| E001 | 输入为空 | "未检测到有效的软件名称，请提供至少一个软件名称或链接。" | 重新输入包含软件名称的文本 |
| E002 | 输入格式不支持 | "仅支持文本格式输入，请勿发送图片或音频。" | 将内容转换为文本后重试 |
| E003 | 无法解析任何条目 | "未能从输入中识别出软件名称，请检查分隔符是否正确。" | 使用逗号或换行分隔软件名称 |
| E004 | 批量处理超限 | "单次处理的软件数量超过 50 个，建议分批输入。" | 将列表拆分为多批次（每批 ≤50 个） |
| E005 | 自定义映射格式错误 | "自定义映射表格式不正确，请提供 JSON 格式的键值对。" | 参考格式：`{"关键词": "类别"}` |
| E006 | 输出格式不支持 | "仅支持表格和 JSON 两种输出格式。" | 指定 `表格` 或 `JSON` |

---

## 6. FAQ 反模式

### 6.1 常见坑

| # | 坑 | 反模式（错误做法） | 正确做法 |
|---|-----|---------------------|----------|
| 1 | 输入超长列表 | 一次性输入 100+ 软件名称 | 分批输入，每批 ≤50 个 |
| 2 | 依赖记忆分类 | 凭印象给软件归类，不核实 | 使用内置知识库 + 关键词匹配 |
| 3 | 忽略歧义 | 同名软件直接归为某一类 | 标注 `[需核实:歧义]` 并说明 |
| 4 | 编造信息 | 不确定时猜测类别 | 使用 `[需核实:类别]` 占位符 |
| 5 | 忽略版本差异 | 按旧版本信息分类新软件 | 标注 `[需核实:版本]` 并提示用户确认 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| "这个软件肯定是效率工具" | 主观臆断，无依据 | 检查关键词匹配度，低置信度时标注需核实 |
| "所有软件我都认识" | 过度自信，忽略小众软件 | 对未匹配条目一律标注 `[需核实:类别]` |
| "分类错了也没关系" | 忽视准确性 | 分类前先核对内置知识库，不确定时标注占位符 |

---

## 7. 渐进式披露

### 7.1 速查卡（新手路径）

1. 输入软件列表（逗号或换行分隔）
2. 获取分类表格
3. 核对 `[需核实]` 项

### 7.2 进阶路径（高级用法）

#### 7.2.1 JSON 输出

在输入末尾追加 `--format json` 即可切换为 JSON 输出。

**示例：**

```
Alfred, VS Code, iStat Menus --format json
```

#### 7.2.2 自定义类别映射

提供关键词对照表（JSON 格式），覆盖默认映射规则。

**示例：**

```
{"关键词": "类别", "Raycast": "效率工具", "CleanMyMac X": "系统工具"}
```

#### 7.2.3 批量处理

- 建议每批不超过 50 个软件名称
- 超长列表请分批输入，避免超时或截断
- 批次之间可对比结果，检查分类一致性

#### 7.2.4 自检命令

| 命令 | 功能 |
|------|------|
| `--selftest` | 运行内置自检，验证分类逻辑 |
| `--version` | 显示当前 Skill 版本号 |

---

## 8. 用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担使用本 Skill 产生的全部责任。本 Skill 提供的分类结果仅供参考，不构成任何形式的专业建议或保证。

2. **禁止反向工程**：使用者不得对本 Skill 的提示词、处理逻辑、内部结构进行反向工程、破解、提取或二次分发。

3. **合规使用**：使用者不得将本 Skill 用于任何违反法律法规或平台规定的用途。

4. **无担保**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性保证。

5. **信息时效**：软件类别和名称可能随版本更新而变化，使用者应自行验证信息的准确性。

---

## 9. 许可证（License）

<!-- professional-license-embedded -->

**MIT License**

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*

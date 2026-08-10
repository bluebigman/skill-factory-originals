---
slug: cheat-sh-pro
name: cheat-sh-pro
displayName: 命令行速查手册
description: 终端内即时获取编程语言与工具代码示例，支持模糊搜索、领域过滤、随机速查与 Markdown 导出，开发调试零切换。
version: 3.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 终端工匠
agent_created: true
trigger_words: ["cheat.sh", "命令行速查", "代码示例查询", "终端查手册", "命令速查", "开发调试速查"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


# cheat-sh-pro — 命令行速查手册

> 一条命令，在终端内获取编程语言与工具的高质量代码示例。支持模糊搜索、领域过滤、随机速查与 Markdown 导出，让开发调试零切换、不打断心流。

## 快速开始 Quick Start

| 场景 | 命令 | 预期结果 |
|------|------|----------|
| 查 Python 列表推导式 | `python run.py search python --query list` | 输出 python 领域下所有与 list 相关的命令及描述 |
| 查 git 提交历史 | `python run.py search git --query log` | 输出 git 领域下与 log 相关的速查条目 |
| 随机学一条命令 | `python run.py random docker` | 随机输出一条 docker 速查命令 |
| 导出全部速查到文件 | `python run.py export --format markdown --output cheats.md` | 生成 Markdown 格式的速查手册文件 |

## 适用场景 When to Use

**什么时候用：**
- 在终端中开发调试，需要快速查阅某语言/工具的语法或用法
- 学习新语言/框架时，希望快速获取核心代码示例
- 在无图形界面的服务器/容器环境中工作，需要离线速查
- 需要将常用命令整理成文档分享给团队

**什么时候不要用：**
- 需要交互式问答或代码执行环境（本工具仅返回静态文本）
- 需要中文翻译（速查内容以英文为主）
- 查询社区尚未收录的冷门工具（返回结果可能为空）

## 能力总览 Capabilities

| 能力 | 命令/参数 | 示例 |
|------|-----------|------|
| 关键词搜索 | `search <domain> --query <keyword>` | `python run.py search python --query lambda` |
| 领域过滤 | `--domain <domain>` | `python run.py search --domain git --query commit` |
| 模糊匹配 | `search` 默认使用 difflib 模糊匹配 | `python run.py search python --query dict` |
| 随机速查 | `random [domain]` | `python run.py random docker` |
| 领域列表 | `list-domains` | `python run.py list-domains` |
| Markdown 导出 | `export --format markdown --output <file>` | `python run.py export --format markdown --output cheats.md` |
| JSON 导出 | `export --format json --output <file>` | `python run.py export --format json --output cheats.json` |
| 预览导出 | `--dry-run` | `python run.py export --format markdown --dry-run` |
| 自检 | `--selftest` | `python run.py --selftest` |
| 详细输出 | `--verbose` | `python run.py search git --query log --verbose` |

## 模块决策表 Decision Table

| 用户意图 | 推荐模块 | 命令示例 |
|----------|----------|----------|
| 查某个语言/工具的特定用法 | `search` | `python run.py search python --query list` |
| 随便学一条命令 | `random` | `python run.py random` |
| 看有哪些领域可用 | `list-domains` | `python run.py list-domains` |
| 整理速查手册 | `export` | `python run.py export --format markdown --output cheats.md` |
| 验证工具是否正常 | `--selftest` | `python run.py --selftest` |

## 示例 Examples

### 示例 1：搜索 Python 的 lambda 用法

## 许可证（License）

```text
MIT License

Copyright (c) {year} {holder}

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

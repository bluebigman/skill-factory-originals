---
slug: aider
name: aider
displayName: Aider 终端结对编程助手
description: 终端内 AI 结对编程，多文件协同编辑、自动 Git 提交、差异审查与回滚。
version: 2.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 代码工坊
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本 Skill 由 AI 辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 代码工坊
agent_created: true
trigger_words: ["aider", "结对编程", "AI改代码", "终端编程助手", "AI写代码", "自动提交"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


# Aider 终端结对编程助手

> 在终端里与 AI 结对编程：加载多个源文件，用自然语言描述修改意图，AI 跨文件理解上下文并生成 diff，你审查后一键接受并自动提交 Git。专为命令行重度用户设计，解决「改代码 → 看 diff → 提交」的重复劳动。

## 快速开始 Quick Start

| 场景 | 命令 | 预期结果 |
|------|------|----------|
| 修改单个文件 | `python run.py --file src/main.py --task "将函数名 foo 改为 bar"` | 生成 diff 预览，输入 `y` 接受并自动提交 |
| 批量替换多个文件 | `python run.py --dir src --pattern "*.py" --task "将所有 print 改为 logging.info"` | 逐文件展示 diff，逐个确认后提交 |
| 预览不落盘 | `python run.py --file src/main.py --task "删除所有 TODO 注释" --dry-run` | 只打印将执行的修改，不写文件不提交 |

## 适用场景 When to Use

**什么时候用：**
- 需要跨多个文件进行一致性修改（如重命名函数、统一日志格式）
- 希望自动生成规范的 Git 提交信息，减少手动 `git add/commit` 操作
- 在提交前想快速审查 AI 生成的 diff，逐文件决定接受或拒绝
- 需要回退最近一次 AI 修改，快速恢复代码状态

**什么时候不要用：**
- 当前目录不是 Git 仓库（无法自动提交）
- 仓库没有任何 commit 记录（无法执行回退）
- 需要处理二进制文件或非文本文件
- 需要跨会话保留对话上下文（每次启动为全新会话）

## 能力总览 Capabilities

| 能力 | 命令/参数 | 示例 |
|------|-----------|------|
| 多文件协同编辑 | `--file` / `--dir` + `--pattern` | `--file src/a.py --file src/b.py --task "..."` |
| 自动 Git 提交 | `--commit`（默认开启） | 接受修改后自动 `git add` + `git commit` |
| 差异审查 | 交互式 `y/n/s` 提示 | 输入 `s` 进入逐文件审查模式 |
| 修改回退 | `--undo` | 回退最近一次 AI 修改（基于 `git checkout`） |
| 批量文件处理 | `--dir` + `--pattern` | 对 `src/` 下所有 `.py` 文件执行统一修改 |
| 预览模式 | `--dry-run` | 只打印 diff 不写盘不提交 |
| 详细日志 | `--verbose` | 输出每个修改决策的明细（替换内容、diff 摘要） |

## 模块决策表 Decision Table

| 用户意图 | 模块/命令 | 读取指引 |
|----------|-----------|----------|
| 修改单个文件 | `FileEditor` + `--file` | 直接指定文件路径，AI 生成修改方案 |
| 批量修改目录 | `BatchProcessor` + `--dir` + `--pattern` | 遍历匹配文件，逐个处理 |
| 回退修改 | `GitHelper.undo()` + `--undo` | 执行 `git checkout` 恢复最近一次修改 |
| 预览修改 | `--dry-run` | 所有写盘操作被守卫，只打印 diff |
| 查看修改明细 | `--verbose` | 输出每个文件的替换详情和 diff 摘要 |

## 示例 Examples

### 示例 1：修改单个文件

```bash
python run.py --file src/main.py --task "将函数名 foo 改为 bar"
```

输出：
```
📄 文件: src/main.py
🔍 修改方案:
  - 将 "def foo" 替换为 "def bar"
  - 将 "foo(" 替换为 "bar("
📝 Diff 预览:
  - def foo(x):  →  def bar(x):
  - foo(1)       →  bar(1)
✅ 接受修改? (y/n/s): y
📦 已提交: 将函数名 foo 改为 bar
```

### 示例 2：批量替换多个文件

```bash
python run.py --dir src --pattern "*.py" --task "将所有 print 改为 logging.info"
```

输出：
```
📁 扫描目录: src
📄 找到 3 个匹配文件
📄 文件: src/a.py
  - print("hello") → logging.info("hello")
✅ 接受修改? (y/n/s): y
📄 文件: src/b.py
  - print("world") → logging.info("world")
✅ 接受修改? (y/n/s): n
⏭️ 跳过修改
📦 已提交: 将所有 print 改为 logging.info
```

### 示例 3：预览模式

```bash
python run.py --file src/main.py --task "删除所有 TODO 注释" --dry-run
```

输出：
```
🔍 预览模式（不写盘）
📄 文件: src/main.py
📝 将执行:
  - 删除第 15 行: # TODO: fix this
  - 删除第 42 行: # TODO: refactor
✅ 预览完成，未写入任何文件
```

## 安装与配置 Installation

### 环境要求

- Python 3.9+
- Git 2.20+
- 操作系统：Linux / macOS / Windows（需支持 `git` 命令）

### 安装步骤

```bash
# 克隆或下载本项目
git clone https://github.com/your-repo/aider-skill.git
cd aider-skill

# 无需额外安装依赖（仅使用标准库）
# 验证安装
python run.py --selftest
```

### 配置

无需环境变量或 API key。所有配置通过命令行参数传入。

## 常见问题 Troubleshooting

| 错误现象 | 原因 | 解决办法 |
|----------|------|----------|
| `错误: 当前目录不是 Git 仓库` | 未初始化 Git | 执行 `git init` 或切换到 Git 仓库目录 |
| `错误: 仓库没有 commit 记录` | 无法执行回退 | 先手动提交一次，再使用 `--undo` |
| `错误: 文件编码不支持` | 文件不是 UTF-8/GBK | 使用 `--encoding` 参数指定编码 |
| `错误: 文件不存在` | 路径错误 | 检查路径是否正确，使用绝对路径 |
| `错误: 没有找到匹配的文件` | `--pattern` 无匹配 | 检查目录和通配符是否正确 |

## 最佳实践 Best Practices

- **使用 `--dry-run` 预览**：在正式修改前先预览，确认修改方案符合预期
- **小步提交**：每次修改一个逻辑单元，便于回退和审查
- **使用 `--verbose` 查看明细**：了解 AI 具体做了什么修改，避免黑盒操作
- **保持 Git 仓库干净**：修改前先提交或 stash 当前工作区，避免混淆
- **注意编码**：处理非 UTF-8 文件时指定 `--encoding` 参数

## 相关资源 Related

- [Aider 官方文档](https://aider.chat/)
- [Git 官方文档](https://git-scm.com/doc)
- [Python 标准库文档](https://docs.python.org/3/library/)

---

## 许可证（License）

```text
MIT License

Copyright (c) 2026 代码工坊

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

---

## 失败处理

- 命令执行失败或返回非零退出码时，程序会输出明确错误信息并给出排查建议。
- 依赖缺失时提示安装命令；网络异常时建议重试并检查连接。
- 异常情况不中断主流程，错误信息包含具体原因（error context），便于定位修复。

## 前置条件

- 本技能开箱即用，无需额外安装依赖。
- 需要 Python 3.9+ 运行环境。
- 涉及网络请求时需保持网络连通。

## 执行步骤

1. 读取输入参数或交互输入。
2. 按技能定义的处理流程执行核心逻辑。
3. 输出结构化结果，并在完成后给出下一步建议。

## 简介

Aider 是一个专注于 开发工具 的自动化技能工具。基于工厂蒸馏流水线增强，提供开箱即用的 自动化处理 能力。

### 核心特性

- **自动化执行**：一键触发完整工作流，无需手动干预
- **智能诊断**：自动检测并修复常见问题
- **标准化输出**：所有产出均符合质量规范

## 安装与配置

### 环境要求

- Python 3.8+
- pip 包管理器

### 安装步骤

```bash
# 克隆或下载本项目
# 安装依赖
pip install -r requirements.txt
```

### 配置

在项目根目录创建 `.env` 文件，配置必要参数。参见 `config.example.yaml`。

## 使用方法

### 基本用法

```bash
python run.py
```

### 高级选项

```bash
python run.py --mode advanced --output-dir ./results
```

### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--mode` | string | `default` | 运行模式 |
| `--output-dir` | string | `./outputs` | 输出目录 |

## 示例

### 示例 1：基础使用

```bash
python run.py --task example
```

输出：
```
✅ 任务完成
📄 结果已保存至 outputs/
```

### 示例 2：批量处理

```bash
python run.py --batch --input data/ --output results/
```

### 示例 3：自定义配置

```bash
python run.py --config custom.yaml --verbose
```

## 常见问题

### Q: 运行报错怎么办？

检查 Python 版本是否 ≥3.8，确保已安装所有依赖。

### Q: 输出结果在哪里？

默认输出到 `outputs/` 目录，可通过 `--output-dir` 自定义。

### Q: 如何处理大批量数据？

使用 `--batch` 模式，配合 `--workers` 参数调整并发数。

## 竞品对标分析

### 对标竞品

| 竞品 | 下载量 | 核心卖点 | 本 Skill 差异化 |
|------|--------|----------|-------|
| Aider | 高 | 终端 AI 结对编程 | 轻量级、无依赖、支持批量处理 |
| Cursor | 高 | IDE 集成 AI | 终端优先，适合命令行用户 |
| Copilot | 高 | 代码补全 | 支持多文件协同编辑和自动提交 |
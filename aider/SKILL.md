---
slug: aider
name: AI结对编程助手
displayName: 终端协作 代码修改 自动提交
description: 终端内AI结对编程，自动提交Git，支持多文件编辑。
version: 1.3.2
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/aider
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: CodeForge Assistant
agent_created: true
trigger_words: ["aider", "结对编程", "AI改代码", "终端编程助手"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# AI 结对编程助手（Aider）使用指南

## 一、能力概览

本技能面向需要在终端环境中与 AI 协作完成代码修改的开发者。它提供了一种交互式工作流：你在终端输入指令，AI 助手读取相关文件、进行修改，并自动将变更提交到 Git 仓库。该工作流特别适合多文件协同编辑的场景，每次修改都会形成独立的提交记录，便于回溯与审查。

## 二、环境准备（前置条件）

在启用本技能前，请确认以下条件已满足：

1. **终端环境**：确保你使用的是类 Unix 终端（如 macOS 的 Terminal、Linux 的 Bash/Zsh），或 Windows 下的 WSL 环境。
2. **Git 仓库**：当前工作目录必须是一个已初始化的 Git 仓库（`git init` 已完成），且具有至少一次提交记录。
3. **Python 环境**：确认已安装 Python 3.9 或更高版本，并可通过 `python3 --version` 验证。
4. **AI 服务访问**：确保网络可访问所配置的 AI 模型服务（如 OpenAI API），且已设置必要的环境变量（如 `OPENAI_API_KEY`）。
5. **工具安装**：通过 `pip install aider-chat` 完成安装，或使用 `aider --version` 检查是否已存在可用版本。

## 三、启动与基础操作

### 3.1 启动会话

在终端直接输入 `aider` 即可启动交互式会话。首次启动时，工具会提示你确认模型类型与 API 密钥配置。

### 3.2 添加文件到会话

使用以下命令将需要修改的文件纳入 AI 的上下文：

```
/aadd path/to/file1.py path/to/file2.js
```

也可以直接在启动时指定文件：

```
aider file1.py file2.js
```

### 3.3 发起修改请求

在 `>` 提示符后，用自然语言描述你的需求。例如：

```
> 将 utils.py 中的日期格式化函数改为使用 datetime 标准库，并同步更新 test_utils.py 中的对应测试用例。
```

### 3.4 确认与提交

AI 完成修改后，会在终端展示 diff（差异对比）。你可以：

- 输入 `y` 接受修改并自动创建 Git 提交；
- 输入 `n` 拒绝修改，AI 将还原文件；
- 输入 `s` 查看每个文件单独的差异，再逐个决定是否接受。

提交信息由 AI 根据修改内容自动生成，格式为 `feat: 简要描述` 或 `fix: 简要描述`。

## 四、常用指令速查

| 指令 | 功能说明 |
|------|----------|
| `/add <文件>` | 将文件加入 AI 上下文 |
| `/drop <文件>` | 将文件移出上下文 |
| `/diff` | 查看当前工作区与暂存区的差异 |
| `/commit` | 手动触发一次提交 |
| `/undo` | 撤销最近一次 AI 修改（回到上一个提交点） |
| `/help` | 查看所有可用指令 |
| `/exit` | 退出会话 |

## 五、执行流程（标准工作流）

以下是一个典型的完整操作序列：

1. **进入项目目录**：`cd your-project/`
2. **启动 Aider**：`aider`
3. **加载相关文件**：`/add src/main.py src/helper.py`
4. **描述任务**：`> 在 main.py 中新增一个命令行参数 --verbose，用于控制日志输出级别，并在 helper.py 中实现对应的日志配置函数。`
5. **查看修改建议**：AI 返回修改后的代码与 diff。
6. **接受修改**：输入 `y`，AI 自动执行 `git add` 与 `git commit`。
7. **验证结果**：运行测试或手动检查代码。
8. **若需调整**：使用 `/undo` 回退，或继续描述新的修改要求。

## 六、输出说明

- **修改后的代码**：AI 会直接修改工作区中的文件内容。
- **差异对比**：每次修改都会在终端呈现清晰的 diff，便于你审查。
- **Git 提交记录**：每次接受的修改都会生成一条独立的提交，提交信息遵循 Conventional Commits 规范。
- **操作反馈**：所有指令执行后，终端会返回成功或失败的状态提示。

## 七、失败处理与常见问题

### 7.1 无法连接 AI 服务

- **现象**：启动时提示 `Connection error` 或 `API key invalid`。
- **处理**：检查环境变量 `OPENAI_API_KEY` 是否已正确设置；确认网络代理是否拦截了请求；尝试更换模型配置（如使用 `--model gpt-4o-mini` 降低资源需求）。

### 7.2 Git 提交失败

- **现象**：提示 `git commit failed`。
- **处理**：确认当前用户已配置 `user.name` 和 `user.email`（执行 `git config --global user.email "you@example.com"`）；检查是否有文件冲突或未解决的合并状态。

### 7.3 AI 修改不符合预期

- **现象**：修改后的代码存在语法错误或逻辑偏差。
- **处理**：立即输入 `/undo` 回退修改；重新描述需求，尽量明确约束条件（如“不要改动函数签名”“保持向后兼容”）；或手动修复后继续会话。

### 7.4 多文件编辑时的冲突

- **现象**：AI 同时修改了多个文件，但部分修改相互矛盾。
- **处理**：使用 `s` 命令逐个文件审查差异，拒绝有问题的文件修改；或先在本地手动解决冲突，再让 AI 继续进行后续任务。

## 八、最佳实践建议

- **小步提交**：每次只要求 AI 完成一个逻辑独立的修改，便于审查与回滚。
- **明确约束**：在描述需求时，主动说明“不要修改测试文件”“保持代码风格不变”等限制。
- **定期同步**：在长时间会话中，每隔一段时间手动 `git pull` 或 `git fetch`，避免与远端仓库脱节。
- **善用上下文**：通过 `/add` 添加必要的依赖文件，帮助 AI 理解代码间的调用关系。但不宜一次添加过多文件，以免超出模型上下文窗口。

## 九、安全与合规提示

- 在包含敏感信息（如密钥、密码）的仓库中使用时，请谨慎描述需求，避免 AI 在提交信息中泄露敏感内容。
- 接受 AI 的修改前，务必阅读 diff，尤其是涉及权限、路径、网络请求等关键逻辑的部分。
- 本工具生成的提交记录会永久保存在 Git 历史中，请勿在公开仓库中提交包含敏感信息的代码。

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

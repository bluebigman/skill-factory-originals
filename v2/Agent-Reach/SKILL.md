---
slug: Agent-Reach
name: Agent-Reach
displayName: 智能体运维 本地管控 批量调度
description: 本地批量运维AI智能体实例，支持启停与状态监控。
version: 3.1.0
license: MIT
source_project: original
source_url: 
copyright_holder: 远控工坊
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 远控工坊
agent_created: true
trigger_words: ["AI智能体本地控制", "Agent-Reach", "本地批量运维AI智能体", "智能体启停", "智能体状态监控", "批量管理AI实例"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->

# Agent-Reach：AI 智能体本地批量运维工具

**Agent-Reach** 是一款面向运维工程师的本地命令行工具，用于批量管理 Linux/macOS 上的 AI 智能体实例。它通过真实进程管理（`subprocess`）和文件系统状态存储，提供实例的批量启动、优雅/强制停止、状态巡检、白名单命令远程执行与结构化报告生成能力，解决多实例手动运维效率低下的问题。

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。

> 本内容由 AI 生成，仅供学习参考

## 快速开始 Quick Start

以下是最短可用路径，帮助您在 1 分钟内上手 Agent-Reach。

| 场景 (Situation) | 操作 (Action) | 预期结果 (Result) |
| :--- | :--- | :--- |
| **启动一个实例** | `python run.py start --names agent-01` | 实例 `agent-01` 被创建并启动，输出包含 PID 和状态文件路径。 |
| **查看所有实例状态** | `python run.py status --all` | 以表格形式输出所有已注册实例的运行状态、PID、资源占用和最近日志。 |
| **批量停止测试环境实例** | `python run.py stop --tag test --mode graceful` | 所有标签为 `test` 的实例收到优雅停止信号，等待退出后状态更新为 `stopped`。 |

## 适用场景 When to Use

**什么时候用？**

- 需要维护 5 台以上 AI 智能体实例，并希望进行统一启停操作。
- 需要定时巡检智能体健康状态（如进程存活、资源占用、日志输出）。
- 需要在多台实例上批量执行预设的运维命令（如磁盘、内存检查）。
- 需要将多实例操作结果汇总成结构化报告（JSON/Markdown）用于分析或归档。

**什么时候不要用？**

- 需要跨公网直接管理实例（Agent-Reach 仅限同一内网或已配置 SSH 隧道环境）。
- 需要修改实例内部代码或文件（Agent-Reach 仅提供运维级命令执行，不提供文件编辑）。
- 需要动态创建或扩容新实例（Agent-Reach 仅管理已注册的实例）。
- 需要图形化管理界面（Agent-Reach 是纯命令行工具）。
- 目标实例是 Windows 系统（仅支持 Linux 或 macOS）。

## 能力总览 Capabilities

以下是 Agent-Reach 的核心能力清单，所有能力均通过 `run.py` 的真实代码实现。

| 能力项 | 命令/参数 | 说明 | 示例 |
| :--- | :--- | :--- | :--- |
| **批量启动** | `start` | 通过 `subprocess.Popen` 启动真实进程，支持按名称、标签、文件列表批量操作。 | `python run.py start --names agent-01,agent-02 --tag test` |
| **批量停止** | `stop` | 支持优雅（`graceful`，发送 SIGTERM）与强制（`force`，发送 SIGKILL）两种模式。 | `python run.py stop --names agent-01 --mode force` |
| **状态巡检** | `status` | 读取实例状态文件，计算真实资源占用（CPU/内存），支持单查与全量轮询。 | `python run.py status --all` |
| **远程执行** | `exec` | 通过 SSH 或 `paramiko` 在目标实例上执行白名单命令，支持超时与指数退避重试。 | `python run.py exec --names agent-01 --command "health_check"` |
| **结果汇总** | `report` | 将多实例操作结果聚合成结构化报告，支持 JSON 与 Markdown 两种格式。 | `python run.py report --format json --output report.json` |
| **预演模式** | `--dry-run` | 所有写操作（启动、停止、报告）的预演模式，只打印将执行的操作，不实际写盘。 | `python run.py stop --names agent-01 --dry-run` |
| **自检** | `--selftest` | 运行内置测试套件，验证核心功能（启动、状态、停止、报告）是否正常。 | `python run.py --selftest` |

## 模块决策表 Decision Table

根据您的意图，选择对应的模块和命令。

| 用户意图 | 推荐模块/命令 | 读取指引 |
| :--- | :--- | :--- |
| 我想快速拉起一批实例 | `start` | 查看 [示例 Examples](#示例-examples) 中的「批量启动」部分。 |
| 我想安全地停掉一个出问题的实例 | `stop` | 查看 [示例 Examples](#示例-examples) 中的「停止实例」部分。 |
| 我想知道所有实例现在是否健康 | `status` | 查看 [示例 Examples](#示例-examples) 中的「状态巡检」部分。 |
| 我想在实例上跑个磁盘检查命令 | `exec` | 查看 [示例 Examples](#示例-examples) 中的「远程执行」部分。 |
| 我想把操作结果整理成报告发给团队 | `report` | 查看 [示例 Examples](#示例-examples) 中的「结果汇总」部分。 |
| 我想先看看停止操作会有什么影响，不想真停 | `stop --dry-run` | 查看 [最佳实践 Best Practices](#最佳实践-best-practices) 中的「安全预演」部分。 |

## 示例 Examples

### 示例 1：批量启动实例

**命令：**

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

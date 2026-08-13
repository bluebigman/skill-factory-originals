---
slug: Agent-Reach
name: Agent-Reach
displayName: 智能体运维 本地管控 批量调度
description: 本地批量运维AI智能体实例，支持启停与状态监控。
version: 4.0.0
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

```bash
python run.py start --names agent-01,agent-02 --tag test
```

**预期输出：**

```text
[2026-08-12 10:00:00] INFO - Starting instance: agent-01 (tag: test)
[2026-08-12 10:00:00] INFO - Instance agent-01 started with PID 12345
[2026-08-12 10:00:00] INFO - Starting instance: agent-02 (tag: test)
[2026-08-12 10:00:00] INFO - Instance agent-02 started with PID 12346
[2026-08-12 10:00:00] INFO - Successfully started 2 instance(s).
```

### 示例 2：停止实例

**命令：**

```bash
python run.py stop --names agent-01 --mode graceful
```

**预期输出：**

```text
[2026-08-12 10:05:00] INFO - Stopping instance: agent-01 (mode: graceful)
[2026-08-12 10:05:00] INFO - Sent SIGTERM to PID 12345
[2026-08-12 10:05:01] INFO - Instance agent-01 stopped successfully.
```

### 示例 3：状态巡检

**命令：**

```bash
python run.py status --all
```

**预期输出：**

```text
+-----------+---------+-------+--------+-----------+
| Name      | Status  | PID   | CPU %  | Memory MB |
+===========+=========+=======+========+===========+
| agent-01  | running | 12345 | 1.2    | 150.3     |
+-----------+---------+-------+--------+-----------+
| agent-02  | stopped | -     | -      | -         |
+-----------+---------+-------+--------+-----------+
```

### 示例 4：远程执行

**命令：**

```bash
python run.py exec --names agent-01 --command "health_check"
```

**预期输出：**

```text
[2026-08-12 10:10:00] INFO - Executing command 'health_check' on agent-01
[2026-08-12 10:10:00] INFO - Output: OK - all systems healthy
```

### 示例 5：结果汇总

**命令：**

```bash
python run.py report --format json --output report.json
```

**预期输出：**

```text
[2026-08-12 10:15:00] INFO - Report generated: report.json (2 instances)
```

## 安装与配置 Installation

### 依赖

- Python 3.8+
- 可选依赖：
  - `filelock`：用于状态文件的并发安全读写（推荐安装）
  - `paramiko`：用于 SSH 远程执行（推荐安装）

### 安装步骤

```bash
# 克隆或下载项目文件
# 安装可选依赖（推荐）
pip install filelock paramiko
```

### 环境变量

| 变量名 | 说明 | 默认值 |
| :--- | :--- | :--- |
| `AGENT_REACH_ROOT` | 实例根目录 | `~/.agent_reach/instances` |
| `AGENT_REACH_SSH_TIMEOUT` | SSH 超时时间（秒） | `10` |
| `AGENT_REACH_SSH_RETRIES` | SSH 重试次数 | `3` |

### 认证方式

远程执行功能支持两种认证方式：
1. **SSH 密钥**：默认使用 `~/.ssh/id_rsa` 密钥进行认证。
2. **密码认证**：通过 `--password` 参数指定密码（不推荐在生产环境使用）。

## 常见问题 Troubleshooting

### 问题 1：启动实例时提示 "Permission denied"

**原因**：当前用户没有权限创建实例目录或启动进程。

**解决办法**：
```bash
# 检查目录权限
ls -la ~/.agent_reach/
# 手动创建目录并设置权限
mkdir -p ~/.agent_reach/instances
chmod 755 ~/.agent_reach
```

### 问题 2：状态巡检显示实例已停止，但进程仍然存在

**原因**：实例可能进入了僵尸状态，或者状态文件未及时更新。

**解决办法**：
```bash
# 手动检查进程
ps aux | grep agent-01
# 强制停止实例
python run.py stop --names agent-01 --mode force
```

### 问题 3：远程执行命令超时

**原因**：目标实例网络不可达，或 SSH 服务未启动。

**解决办法**：
```bash
# 检查网络连通性
ping -c 3 <instance-ip>
# 检查 SSH 服务
ssh -o ConnectTimeout=5 <instance-ip> "echo ok"
```

### 问题 4：报告生成失败，提示 "No instances found"

**原因**：实例目录为空，或没有已注册的实例。

**解决办法**：
```bash
# 检查实例目录
ls -la ~/.agent_reach/instances/
# 启动至少一个实例后再生成报告
python run.py start --names agent-01
```

## 最佳实践 Best Practices

### 安全预演

在执行任何写操作（启动、停止、报告）之前，建议先使用 `--dry-run` 参数进行预演：

```bash
# 预演停止操作
python run.py stop --names agent-01 --dry-run

# 预演启动操作
python run.py start --names agent-01 --dry-run
```

### 批量操作建议

- 使用标签（`--tag`）对实例进行分组管理，便于批量操作。
- 批量操作时建议使用 `--max-workers` 参数控制并发数，避免资源竞争。
- 停止实例时优先使用 `graceful` 模式，确保实例正常退出。

### 日志管理

- 每个实例的日志保存在 `~/.agent_reach/instances/<name>/agent.log`。
- 建议定期清理旧日志，避免磁盘空间不足。
- 使用 `--verbose` 参数查看详细操作日志。

### 安全提醒

- 远程执行功能仅支持白名单命令，请勿修改 `ALLOWED_COMMANDS` 配置。
- 不要在命令行中直接传递敏感信息（如密码），建议使用 SSH 密钥认证。
- 定期备份 `~/.agent_reach` 目录，防止数据丢失。

## 相关资源 Related

- [GitHub 仓库](https://github.com/your-repo/agent-reach)（示例）
- [Python subprocess 文档](https://docs.python.org/3/library/subprocess.html)
- [paramiko 文档](https://docs.paramiko.org/)
- [filelock 文档](https://py-filelock.readthedocs.io/)

## 许可证（License）

```text
MIT License

Copyright (c) 2026 远控工坊

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
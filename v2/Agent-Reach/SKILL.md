---
slug: Agent-Reach
name: AI智能体远程控制
displayName: 智能体运维 远程管控 批量调度
description: 远程批量运维AI智能体实例，支持启停与状态监控。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 远控工坊
agent_created: true
trigger_words: ["AI智能体远程控制", "Agent-Reach", "远程批量运维AI智能体", "智能体启停", "智能体状态监控", "批量管理AI实例"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# AI智能体远程控制（Agent-Reach）技能文档

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 能力项 | 说明 | 支持范围 |
|--------|------|----------|
| 批量启动 | 同时拉起多个指定智能体实例 | 支持按名称、标签、文件列表批量操作 |
| 批量停止 | 优雅关闭或强制终止多个实例 | 支持超时强杀与优雅退出两种模式 |
| 状态巡检 | 获取实例运行状态、资源占用、日志尾部 | 支持单查与全量轮询 |
| 远程执行 | 在目标实例上执行预设运维命令 | 仅限白名单命令集 |
| 结果汇总 | 将多实例操作结果聚合成结构化报告 | 输出 JSON / Markdown 两种格式 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不支持跨公网直连 | 仅限同一内网或已配置 SSH 隧道的环境 |
| 不支持实例内部代码修改 | 只能执行运维级操作，不提供文件编辑能力 |
| 不支持动态扩容 | 无法自动创建新实例，仅管理已有实例 |
| 不支持图形界面 | 纯命令行交互，无 Web UI |
| 不支持 Windows 目标机 | 目标实例必须运行 Linux 或 macOS |

### 1.3 适用对象

- 需要维护 5 台以上 AI 智能体实例的运维工程师
- 需要定时巡检智能体健康状态的数据团队
- 需要批量发布/下线智能体的平台管理员

---

## 二、触发方式

### 2.1 触发词

- 主触发词：`AI智能体远程控制`、`Agent-Reach`
- 同义场景词：`批量管理AI实例`、`智能体运维`、`远程启停智能体`

### 2.2 场景映射表

| 用户说（大白话） | 触发动作 |
|------------------|----------|
| "帮我把那三个推荐模型实例停掉" | 批量停止指定实例 |
| "看看现在所有智能体跑得怎么样" | 全量状态巡检 |
| "把测试环境那批智能体全部启动" | 按标签批量启动 |
| "检查一下实例 agent-07 的日志" | 单实例日志获取 |
| "给所有实例执行一次健康检查命令" | 批量执行白名单命令 |

---

## 三、标准流程

### 3.1 前置条件

| 条件项 | 要求 | 校验方式 |
|--------|------|----------|
| 操作系统 | Linux（主流发行版）或 macOS 10.15+ | `uname -a` |
| 依赖软件 | Python 3.8+、sshpass（或已配置免密）、jq | `python3 --version && which sshpass jq` |
| 网络环境 | 可访问 GitHub 或内部代码仓库 | `curl -sI https://github.com -m 5` |
| 存储空间 | `$HOME/tools` 下至少 2GB 可用 | `df -h $HOME/tools` |
| 权限 | 普通用户即可，安装依赖时可能需要 sudo | `sudo -v` 测试 |

### 3.2 执行步骤

1. **收集输入**：接收用户提供的实例列表、操作类型（start/stop/status/exec）、可选参数（超时时间、并发数）。
2. **格式校验**：检查实例名是否符合 `^[a-zA-Z0-9_-]{1,64}$`，操作类型是否在枚举范围内。
3. **连接预检**：对每个目标实例执行 `ssh -o ConnectTimeout=5` 探测连通性，失败则标记为 `unreachable`。
4. **执行操作**：
   - 启动：`ssh <host> "nohup <agent_start_cmd> > /var/log/agent.log 2>&1 &"`
   - 停止：先发 `SIGTERM`，等待 10 秒，未退出则发 `SIGKILL`
   - 状态：`ssh <host> "ps aux | grep <agent_name> | grep -v grep"`
   - 执行：仅允许白名单命令（见 3.4 节）
5. **结果收集**：按实例维度汇总退出码、stdout、stderr。
6. **完整性校验**：确认返回结果中实例数量与输入一致，缺失项标记为 `[需核实:实例ID]`。
7. **输出报告**：生成结构化报告，包含每个实例的操作结果、耗时、异常信息。

### 3.3 输出规范

```json
{
  "operation": "batch_start",
  "timestamp": "2025-01-15T10:30:00Z",
  "total": 5,
  "success": 4,
  "failed": 1,
  "results": [
    {
      "instance_id": "agent-01",
      "status": "success",
      "exit_code": 0,
      "message": "started in 2.3s"
    },
    {
      "instance_id": "agent-02",
      "status": "failed",
      "exit_code": 1,
      "message": "port 8080 already in use"
    }
  ]
}
```

### 3.4 白名单命令集

| 命令 | 用途 | 参数约束 |
|------|------|----------|
| `healthcheck` | 健康检查 | 无参数 |
| `log_tail` | 查看日志尾部 | `-n <行数>`，行数 ≤ 500 |
| `disk_usage` | 磁盘占用 | 无参数 |
| `model_reload` | 重载模型 | 无参数 |

---

## 四、置信度门控

当出现以下情况时，**不得编造**结果，必须输出占位符 `[需核实:字段名]`：

| 场景 | 占位示例 |
|------|----------|
| 实例列表不完整 | `[需核实:缺失的实例ID]` |
| 命令执行超时无返回 | `[需核实:agent-03执行结果]` |
| 日志文件不存在 | `[需核实:agent-05日志路径]` |
| 状态信息冲突（进程存在但端口未监听） | `[需核实:agent-08实际状态]` |

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | 输入格式错误 | "实例ID格式不正确，应为字母/数字/下划线/连字符，长度1-64" | 重新输入，参考示例 `agent-01` |
| `E002` | 实例不可达 | "无法连接到实例，请检查网络或SSH配置" | 运行 `ssh <host> -o ConnectTimeout=5` 手动测试 |
| `E003` | 操作类型不支持 | "仅支持 start/stop/status/exec 四种操作" | 检查操作类型拼写 |
| `E004` | 白名单命令违规 | "该命令不在允许列表中，请使用 healthcheck/log_tail/disk_usage/model_reload" | 更换为白名单命令 |
| `E005` | 并发数超限 | "并发数不能超过20，当前请求为25" | 降低并发数或分批执行 |
| `E006` | 依赖缺失 | "缺少 jq 或 sshpass，请先安装" | `brew install jq sshpass`（macOS）或 `apt install jq sshpass`（Linux） |
| `E007` | 存储空间不足 | "$HOME/tools 剩余空间不足2GB" | 清理旧日志或迁移数据 |

---

## 六、FAQ 反模式

### 6.1 常见坑

| 坑 | 反模式描述 | 正确做法 |
|----|------------|----------|
| 坑1：忽略 SSH 超时 | 使用默认 SSH 超时（可能 120 秒），导致批量操作卡死 | 显式设置 `-o ConnectTimeout=5`，失败立即标记 |
| 坑2：并发无上限 | 一次性对 50 个实例并发操作，打爆本机连接数 | 限制并发 ≤ 20，使用信号量控制 |
| 坑3：停止后不确认 | 发送 SIGTERM 后直接报告成功，实际进程还在 | 等待 10 秒后 `ps` 确认，未退出再 SIGKILL |
| 坑4：日志无限拉取 | 直接 `cat` 整个日志文件，可能几个 GB | 使用 `tail -n 500` 限制行数 |
| 坑5：忽略退出码 | 只看 stdout 不看 `$?`，误判成功 | 每次 SSH 执行后检查退出码，非 0 即失败 |

### 6.2 反模式对照表

| 反模式 | 问题 | 替代方案 |
|--------|------|----------|
| 用 `kill -9` 直接强杀所有实例 | 可能损坏模型文件 | 先 SIGTERM，10 秒后未退出再 SIGKILL |
| 把所有实例的日志合并到一个文件 | 难以定位问题 | 按实例分文件存储，文件名含实例 ID |
| 在循环里串行执行所有操作 | 50 个实例要等 50 倍时间 | 使用 `xargs -P 10` 或 Python 并发 |
| 手动记录操作结果 | 容易遗漏和出错 | 使用脚本自动生成 JSON 报告 |

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 查看版本
agent-reach --version

# 自检
agent-reach --selftest

# 批量启动（按标签）
agent-reach start --tag test-env --concurrency 10

# 批量停止（按文件列表）
agent-reach stop --file instances.txt

# 状态巡检（全部）
agent-reach status --all

# 单实例日志
agent-reach exec agent-01 log_tail -n 100
```

### 7.2 新手路径（首次使用）

1. 运行 `agent-reach --selftest` 验证环境
2. 准备一个包含 2-3 个实例 ID 的文本文件
3. 执行 `agent-reach status --file instances.txt` 查看状态
4. 执行 `agent-reach start --file instances.txt` 启动实例
5. 再次执行 status 确认启动成功

### 7.3 进阶路径（深度使用）

1. 编写自定义白名单命令扩展（需修改配置文件）
2. 设置 cron 定时任务，每 5 分钟执行一次状态巡检
3. 将 JSON 报告接入内部监控看板
4. 使用标签体系管理不同环境（prod/staging/dev）的实例
5. 配置异常自动告警（当 status 返回 failed 时触发通知）

---

## 八、参数速查表

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--selftest` | 标志 | 否 | - | 运行环境自检 |
| `--version` | 标志 | 否 | - | 显示版本号 |
| `start/stop/status/exec` | 子命令 | 是 | - | 操作类型 |
| `--tag` | 字符串 | 否 | - | 按标签筛选实例 |
| `--file` | 路径 | 否 | - | 实例列表文件（每行一个 ID） |
| `--all` | 标志 | 否 | - | 操作所有实例 |
| `--concurrency` | 整数 | 否 | 5 | 并发数（1-20） |
| `--timeout` | 整数 | 否 | 30 | 单实例操作超时（秒） |
| `-n` | 整数 | 否 | 100 | 日志行数（≤500） |

---

## 九、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 进行远程操作所产生的一切后果，包括但不限于数据丢失、服务中断、配置错误等。本 Skill 提供的是操作框架，不包含对特定环境的适配保证。
2. **禁止反向工程**：不得对本 Skill 的代码、逻辑、文档进行反向工程、反编译、破解或试图提取底层算法。
3. **合规使用**：使用者应确保其操作行为符合所在组织的信息安全规范，且仅对有权管理的实例执行操作。
4. **无担保声明**：本 Skill 按"原样"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权保证。

---

## 十、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

```
MIT License

Copyright (c) 2025 原创作者（自持版权）

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

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证适用性。*

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agent-loop-engine
name: agent-loop-engine
displayName: 代理编排 状态内核 长期任务
description: 轻量级状态内核，管理长期运行AI代理团队，支持持久目标与可验证交接。
version: 1.0.4
rules_version: cpr-20260814-n426
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agent-loop-engine
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Ling Xiao
agent_created: true
trigger_words: ["agent-loop-engine", "循环引擎", "代理编排", "状态内核", "长期运行代理", "多代理协作", "任务状态机"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# agent-loop-engine 技能手册

## 一、能力边界（一页纸速查卡）

### 能做什么

| 能力项 | 说明 | 典型场景 |
|--------|------|----------|
| 状态持久化 | 将代理运行中间状态写入 `--state-file` 指定的 JSON 文件 | 中断后恢复、跨进程共享 |
| 可验证交接 | 每个代理完成后输出 `handoffs` 字段，记录交接目标与校验哈希 | 多代理流水线、人工审核节点 |
| 节奏控制 | 通过 `--interval` 控制代理轮询间隔，模拟异步行为 | 定时任务、限流场景 |
| 目标管理 | 支持持久目标（persistent goals）的注册、更新与完成判定 | 长期项目跟踪、多阶段任务 |
| 自检能力 | `--selftest` 验证内核完整性，`--version` 输出版本信息 | 部署验证、故障排查 |

### 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不提供分布式锁 | 多进程同时写同一状态文件时，不保证原子性 |
| 不内置代理逻辑 | 代理的 `run(state)` 方法需由使用者自行实现 |
| 不处理网络通信 | 代理间通信需自行设计，内核只负责状态流转 |
| 不保证任务成功 | 内核只保证状态正确记录，不干预代理执行结果 |

### 适用对象

- 需要长期运行（小时/天级）的 AI 代理团队
- 需要可审计、可恢复的异步任务流水线
- 需要明确交接边界的人机协作系统

---

## 二、触发方式

### 触发词

`agent-loop-engine`、`循环引擎`、`代理编排`、`状态内核`、`长期运行代理`、`多代理协作`、`任务状态机`

### 场景映射表

| 你的需求（大白话） | 对应的触发方式 |
|-------------------|----------------|
| "我想让几个 AI 代理轮流干活，干完一个传给下一个" | 使用 `handoffs` 字段设计交接链 |
| "任务跑了一半断了，重启后想接着跑" | 使用 `--state-file` 持久化状态 |
| "我想控制代理多久检查一次任务" | 使用 `--interval` 参数 |
| "我想确认代理是不是真的完成了" | 查看 `status` 字段与 `handoffs` 中的校验哈希 |

---

## 三、标准处理流程

### 前置条件

1. Python 3.9+ 环境
2. 已安装 agent-loop-engine 包（`pip install agent-loop-engine`）
3. 自定义代理类已实现 `run(state)` 接口

### 执行步骤

#### 第一步：最小示例（速查）

```bash
# 运行内置示例代理，输出状态 JSON
agent-loop-engine --selftest

# 查看版本
agent-loop-engine --version
```

预期输出（`--selftest`）：

```json
{
  "status": "completed",
  "handoffs": [],
  "state": {"iteration": 1, "last_error": null}
}
```

#### 第二步：自定义代理

创建 `my_agent.py`：

```python
from agent_loop_engine import BaseAgent

class MyAgent(BaseAgent):
    def run(self, state):
        # 你的业务逻辑
        state["count"] = state.get("count", 0) + 1
        return {"status": "running", "state": state}
```

#### 第三步：带状态文件的运行

```bash
agent-loop-engine --agent my_agent.MyAgent --state-file ./state.json --interval 5
```

中断后重新运行同一命令，观察状态恢复：

```bash
# 第二次运行，state.json 中的 count 会从上次的值继续
```

#### 第四步：错误码验证

故意让代理抛出异常，观察错误码 `E1004`：

```python
class BadAgent(BaseAgent):
    def run(self, state):
        raise RuntimeError("模拟故障")
```

```bash
agent-loop-engine --agent my_agent.BadAgent --state-file ./state.json
# 输出包含 "error_code": "E1004"
```

### 输出规范

所有输出均为 JSON 格式，包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | string | `running` / `completed` / `failed` / `paused` |
| `handoffs` | array | 交接记录，每项含 `target`、`hash`、`timestamp` |
| `state` | object | 代理自定义状态，可持久化 |
| `error_code` | string | 错误码（仅失败时出现） |

---

## 四、置信度门控

当信息不足时，内核不会编造数据，而是输出占位符：

| 场景 | 占位符 | 示例 |
|------|--------|------|
| 代理未返回 `status` | `[需核实:status]` | `{"status": "[需核实:status]"}` |
| 交接目标未指定 | `[需核实:handoff_target]` | `{"handoffs": [{"target": "[需核实:handoff_target]"}]}` |
| 状态文件损坏 | `[需核实:state_integrity]` | 输出警告并跳过恢复 |

**传播机制**：占位符会沿交接链向下游传播，直到被真实数据替换或触发 `E1003` 错误。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E1001` | 状态文件无法写入 | "状态文件路径不可写，请检查权限" | 1. 检查目录权限；2. 更换 `--state-file` 路径 |
| `E1002` | 代理类未实现 `run` 方法 | "代理类缺少 run(state) 接口" | 1. 确认继承 `BaseAgent`；2. 实现 `run` 方法 |
| `E1003` | 状态文件损坏 | "状态文件 JSON 解析失败，无法恢复" | 1. 备份原文件；2. 删除后重新运行 |
| `E1004` | 代理执行异常 | "代理运行时抛出未捕获异常，已记录堆栈" | 1. 查看 `state.last_error`；2. 修复代理逻辑；3. 使用 `--state-file` 恢复 |
| `E1005` | 交接目标不存在 | "handoffs 中指定的 target 未注册" | 1. 检查交接目标名称；2. 确认目标代理已加载 |

---

## 六、FAQ 反模式

### 反模式 1：忽略状态文件

**错误做法**：每次运行都不指定 `--state-file`，导致中断后从头开始。

**正确做法**：始终使用 `--state-file`，并定期备份。

### 反模式 2：在 `run()` 中做耗时操作

**错误做法**：代理的 `run()` 方法执行 10 分钟的网络请求，阻塞内核。

**正确做法**：将耗时操作放入子线程，`run()` 快速返回 `status: "paused"`，配合 `--interval` 轮询结果。

### 反模式 3：不检查 `handoffs` 哈希

**错误做法**：交接时直接信任上游数据，不验证哈希。

**正确做法**：在代理入口处校验 `handoffs[].hash`，不匹配则返回 `E1005`。

### 反模式 4：错误码处理一刀切

**错误做法**：所有错误码都按同一逻辑重试。

**正确做法**：区分可恢复错误（`E1004`）与不可恢复错误（`E1003`），分别设计重试与终止策略。

### 反模式 5：状态文件多人共用

**错误做法**：多个进程同时写同一个 `state.json`。

**正确做法**：每个代理实例使用独立状态文件，或引入外部锁机制。

---

## 七、渐进式披露

### 速查卡（30 秒上手）

```bash
# 1. 自检
agent-loop-engine --selftest

# 2. 运行自定义代理（带状态持久化）
agent-loop-engine --agent my_agent.MyAgent --state-file ./state.json

# 3. 查看输出 JSON 的 status 和 handoffs 字段
```

### 新手路径（5 分钟）

1. 阅读「能力边界」了解适用范围
2. 运行速查卡中的最小示例
3. 查看输出 JSON，理解 `status` 和 `handoffs` 字段
4. 尝试添加 `--state-file`，中断后重新运行，观察恢复行为

### 进阶路径（30 分钟）

1. 阅读「标准处理流程」中的参数表与执行步骤
2. 自定义代理类，实现 `run(state)` 接口
3. 使用 `--interval` 控制节奏，模拟真实异步场景
4. 检查错误码 `E1004` 的触发条件，设计代理异常恢复逻辑
5. 阅读「置信度门控」，理解占位符的传播机制

---

## 八、参数参考表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--agent` | string | 无 | 代理类路径，格式 `module.ClassName` |
| `--state-file` | string | 无 | 状态文件路径，启用持久化 |
| `--interval` | int | 1 | 轮询间隔（秒），最小 0.1 |
| `--selftest` | flag | 无 | 运行内置自检 |
| `--version` | flag | 无 | 输出版本号 |
| `--max-iterations` | int | 1000 | 最大迭代次数，防止死循环 |

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于数据丢失、任务失败、系统故障等。
2. **禁止反向工程**：不得对本 Skill 的底层实现进行反向工程、反编译或试图提取源代码（除非适用法律允许）。
3. **无担保**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。
4. **使用限制**：不得将本 Skill 用于任何违反法律法规或侵犯第三方权益的用途。

<!-- user-agreement-injected -->

---

## 许可证（License）

MIT License

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

<!-- professional-license-embedded -->

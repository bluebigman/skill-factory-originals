---
slug: agent-loop-engine
name: agent-loop-engine
displayName: 代理编排 状态内核 长期任务
description: 管理长期运行AI代理团队，支持持久目标与可验证交接。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Ling Xiao
agent_created: true
trigger_words: ["agent-loop-engine", "循环引擎", "代理编排", "状态内核", "长期运行代理", "任务交接", "状态持久化"]
---

> 本内容由 AI 生成，仅供学习参考 <!-- ai-generated-notice -->

# agent-loop-engine Skill 文档

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 示例 |
|--------|------|------|
| 状态持久化 | 将代理运行状态保存至文件，支持中断恢复 | `--state-file ./state.json` |
| 多代理编排 | 管理多个代理实例，按序或按条件执行 | 定义 3 个代理依次处理数据 |
| 可验证交接 | 代理间通过 `handoffs` 字段传递任务，交接可追溯 | 代理 A 输出 `handoffs: ["agent_b"]` |
| 循环控制 | 通过 `--interval` 控制轮询节奏 | `--interval 5` 每 5 秒执行一次 |
| 置信度门控 | 信息不足时输出占位符，不编造数据 | 输出 `[需核实:field_name]` |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 非通用任务框架 | 不提供任务调度、队列管理、分布式计算能力 |
| 无内置代理实现 | 必须由使用者自定义代理类并实现 `run(state)` 接口 |
| 不保证任务成功 | 不承诺任务必然完成，仅提供状态管理与交接机制 |
| 非实时系统 | 不适用于毫秒级响应场景，最小间隔受限于系统调度 |

### 1.3 适用对象

- 需要运行数小时至数天的 AI 代理任务
- 需要多代理协作且交接过程需留痕的场景
- 需要中断后恢复执行状态的开发项目

---

## 二、触发方式

### 2.1 触发词

| 触发词 | 场景说明 |
|--------|----------|
| `agent-loop-engine` | 直接调用引擎 |
| `循环引擎` | 中文场景下的别名 |
| `代理编排` | 需要管理多个代理时 |
| `状态内核` | 关注状态持久化能力时 |
| `长期运行代理` | 任务需要长时间执行时 |
| `任务交接` | 代理间需要传递任务时 |
| `状态持久化` | 需要保存/恢复运行状态时 |

### 2.2 场景映射表

| 用户需求（大白话） | 对应能力 | 使用方式 |
|-------------------|----------|----------|
| "我的代理跑了一天后崩了，能接着跑吗？" | 状态持久化 | 使用 `--state-file` 参数 |
| "我有 3 个代理要依次处理数据" | 多代理编排 | 定义代理列表，按序执行 |
| "代理 A 做完后怎么通知代理 B？" | 可验证交接 | 在 `run()` 中设置 `handoffs` 字段 |
| "我不想让代理一直空转" | 循环控制 | 设置 `--interval` 参数 |
| "代理遇到不确定的信息怎么办？" | 置信度门控 | 输出 `[需核实:字段名]` 占位符 |

---

## 三、标准处理流程

### 3.1 前置条件

| 条件 | 要求 | 验证方式 |
|------|------|----------|
| Python 版本 | 3.9+ | `python --version` |
| 包安装 | `pip install agent-loop-engine` | `pip show agent-loop-engine` |
| 代理类实现 | 自定义类包含 `run(state)` 方法 | 导入测试 |
| 状态文件权限 | 可读写（如使用 `--state-file`） | `touch ./test-state.json` |

### 3.2 执行步骤

#### 步骤 1：最小示例（验证安装）

```python
# minimal_agent.py
from agent_loop_engine import LoopEngine

class MyAgent:
    def run(self, state):
        state["count"] = state.get("count", 0) + 1
        return {"status": "running", "count": state["count"]}

engine = LoopEngine(agents=[MyAgent()], max_iterations=3)
result = engine.execute()
print(result)
```

执行命令：

```bash
python minimal_agent.py
```

预期输出（JSON 格式）：

```json
{
  "status": "completed",
  "iterations": 3,
  "final_state": {"count": 3},
  "handoffs": []
}
```

#### 步骤 2：添加状态持久化

```bash
python minimal_agent.py --state-file ./my-state.json
```

中断后重新运行，观察输出中 `final_state` 是否包含上次的 `count` 值。

#### 步骤 3：多代理交接

```python
# multi_agent.py
class AgentA:
    def run(self, state):
        state["step_a"] = "done"
        return {"status": "handoff", "handoffs": ["agent_b"]}

class AgentB:
    def run(self, state):
        state["step_b"] = "done"
        return {"status": "completed", "handoffs": []}

engine = LoopEngine(agents=[AgentA(), AgentB()], max_iterations=5)
result = engine.execute()
```

#### 步骤 4：设置循环间隔

```bash
python multi_agent.py --interval 2
```

每 2 秒执行一轮代理循环。

### 3.3 输出规范

引擎输出为 JSON 对象，包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | string | `running` / `completed` / `error` / `handoff` |
| `iterations` | int | 已执行的循环次数 |
| `final_state` | object | 最终状态字典 |
| `handoffs` | array | 待交接的代理名称列表 |
| `error` | object | 错误信息（仅 `status=error` 时出现） |

---

## 四、置信度门控

### 4.1 占位符规则

当代理在执行过程中遇到以下情况时，**不得编造数据**，必须输出占位符：

| 情况 | 占位符格式 | 示例 |
|------|-----------|------|
| 外部 API 返回超时 | `[需核实:api_response]` | `[需核实:user_profile]` |
| 数据库查询无结果 | `[需核实:db_record]` | `[需核实:order_123]` |
| 用户输入缺失 | `[需核实:user_input]` | `[需核实:preferred_time]` |
| 计算结果超出预期范围 | `[需核实:calculation]` | `[需核实:total_amount]` |

### 4.2 占位符传播机制

1. 代理 A 输出 `[需核实:field_x]`
2. 引擎检测到占位符，将 `status` 置为 `handoff`
3. 代理 B 收到包含占位符的状态
4. 代理 B 可尝试补充信息，若仍无法获取，继续传递占位符
5. 最终输出中保留所有未解决的占位符

### 4.3 边界值

- 占位符最大长度：256 字符
- 单次运行最多保留 50 个未解决占位符
- 超过限制时，引擎自动截断并标记 `truncated: true`

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E1001` | 代理类未实现 `run()` 方法 | "代理类必须实现 run(state) 接口" | 检查代理类定义，添加 `run` 方法 |
| `E1002` | 状态文件无法写入 | "状态文件写入失败，请检查路径权限" | 确认目录存在且有写权限 |
| `E1003` | 循环次数超过上限 | "已达到最大迭代次数，任务终止" | 调整 `max_iterations` 参数 |
| `E1004` | 代理异常未捕获 | "代理执行抛出未处理异常" | 在 `run()` 中添加 try-except，返回错误状态 |
| `E1005` | 交接目标不存在 | "交接目标代理未在代理列表中注册" | 检查 `handoffs` 字段中的代理名称 |
| `E1006` | 状态文件格式损坏 | "状态文件解析失败，可能已损坏" | 删除或备份旧状态文件，重新运行 |

### 5.1 错误处理示例

```python
class SafeAgent:
    def run(self, state):
        try:
            # 业务逻辑
            result = self.process(state)
            return {"status": "completed", "data": result}
        except Exception as e:
            return {
                "status": "error",
                "error_code": "E1004",
                "error_message": str(e)
            }
```

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 常见坑 | 反模式（错误做法） | 正模式（推荐做法） |
|--------|-------------------|-------------------|
| 代理状态丢失 | 在 `run()` 中直接修改全局变量 | 始终通过 `state` 参数读写状态 |
| 无限循环 | 不设置 `max_iterations` | 始终设置最大迭代次数 |
| 交接失败 | 在 `handoffs` 中写入未注册的代理名 | 先注册所有代理，再设置交接 |
| 忽略错误 | 捕获异常后静默返回 | 返回 `status: "error"` 并附带错误码 |
| 状态文件冲突 | 多个进程同时写同一状态文件 | 使用独立状态文件或加锁机制 |

### 6.2 反模式示例

```python
# 反模式：不设置最大迭代次数
engine = LoopEngine(agents=[MyAgent()])  # 可能无限运行

# 正模式：设置最大迭代次数
engine = LoopEngine(agents=[MyAgent()], max_iterations=100)
```

```python
# 反模式：交接未注册的代理
return {"status": "handoff", "handoffs": ["ghost_agent"]}

# 正模式：交接已注册的代理
return {"status": "handoff", "handoffs": ["agent_b"]}
```

---

## 七、渐进式披露

### 7.1 速查卡（30 秒上手）

```bash
# 安装
pip install agent-loop-engine

# 最小运行
python your_agent.py

# 带状态持久化
python your_agent.py --state-file ./state.json

# 控制节奏
python your_agent.py --interval 5

# 查看版本
agent-loop-engine --version

# 自检
agent-loop-engine --selftest
```

### 7.2 分层次阅读路径

#### 新手路径（首次使用）

1. 阅读「一、能力边界」了解适用范围
2. 运行「3.2 步骤 1」的最小示例
3. 查看输出 JSON，理解 `status` 和 `handoffs` 字段
4. 尝试添加 `--state-file`，中断后重新运行，观察恢复行为

#### 进阶路径（深度集成）

1. 阅读「三、标准处理流程」中的参数表与执行步骤
2. 自定义代理类，实现 `run(state)` 接口
3. 使用 `--interval` 控制节奏，模拟真实异步场景
4. 检查错误码 `E1004` 的触发条件，设计代理异常恢复逻辑
5. 阅读「四、置信度门控」，理解占位符的传播机制

#### 专家路径（性能调优）

1. 分析状态文件大小与读写频率，优化持久化策略
2. 设计多级代理交接拓扑，减少不必要的状态传递
3. 结合外部监控工具，跟踪 `status` 变化与 `handoffs` 流转

---

## 八、参数参考表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--state-file` | string | 无 | 状态持久化文件路径 |
| `--interval` | float | 0 | 循环间隔（秒） |
| `--max-iterations` | int | 100 | 最大迭代次数 |
| `--selftest` | flag | 无 | 运行自检 |
| `--version` | flag | 无 | 显示版本号 |
| `--verbose` | flag | 无 | 输出详细日志 |

---

## 九、用户协议

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于数据丢失、任务失败、系统故障等。
2. **禁止反向工程**：不得对本 Skill 的底层实现进行反向工程、反编译或试图提取源代码（除非适用法律允许）。
3. **无担保**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保。
4. **使用限制**：不得将本 Skill 用于任何违反法律法规或侵犯第三方权益的用途。

<!-- user-agreement-injected -->

---

## 十、许可证（License）

### MIT License

```
MIT License

Copyright (c) 2024 Ling Xiao

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档。*

---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agent-loop-engine
name: agent-loop-engine
displayName: 循环引擎 代理编排 状态内核
description: 轻量级循环状态内核，管理长期运行的AI代理团队，支持持久目标与可验证交接。
version: 1.0.1
rules_version: cpr-20260808-n152
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agent-loop-engine
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["agent-loop-engine", "循环引擎", "代理编排", "状态内核", "长期运行代理", "持久目标", "待办执行", "证据日志", "可验证交接"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# agent-loop-engine — 循环引擎 · 代理编排 · 状态内核

## 一、能力边界：一页纸速查卡

### 1.1 核心定位

本 Skill 是一套**轻量级循环工程状态内核**的设计蓝图与实现指南。它面向需要**长期运行**的 AI 代理团队（例如：持续监控、周期报告、多阶段任务流水线），提供持久目标管理、配额感知唤醒、可执行待办、证据日志和可验证交接的完整方案。

### 1.2 能做（5 项核心能力）

| 序号 | 能力项 | 说明 | 典型应用场景 |
|------|--------|------|--------------|
| 1 | **持久目标管理** | 将用户输入的目标拆解为可持久化的状态对象，跨会话保留 | 月度市场监测、长期竞品跟踪 |
| 2 | **配额感知自动唤醒** | 根据时间/事件/资源配额条件，自动触发代理执行下一轮循环 | 每日定时抓取、达到阈值触发告警 |
| 3 | **可执行待办队列** | 将目标拆解为原子化待办项，支持状态流转（待办→进行中→完成） | 多步骤数据处理流水线 |
| 4 | **证据日志记录** | 每次执行动作均记录可追溯的证据（输入快照、输出摘要、时间戳） | 审计合规、结果复核 |
| 5 | **可验证交接** | 代理间交接时生成交接凭证，接收方可验证完整性与来源 | 多代理协作、任务转派 |

### 1.3 不能做（明确边界）

| 序号 | 限制项 | 说明 |
|------|--------|------|
| 1 | **不提供运行时环境** | 本 Skill 是设计规范与代码模板，不包含实际执行代理的运行时容器 |
| 2 | **不替代消息队列** | 不提供跨进程/跨机器的消息传递能力，仅管理单进程内的状态流转 |
| 3 | **不处理非结构化目标** | 输入目标必须为结构化描述（含可量化指标），否则无法拆解 |
| 4 | **不保证外部系统可用性** | 若代理依赖外部 API/数据库，其可用性由外部系统决定 |
| 5 | **不支持动态扩容** | 代理数量在初始化时固定，运行期不支持动态增减 |

### 1.4 适用对象

- **适用**：需要长期运行的 AI 代理团队（3-20 个代理）、周期性任务编排、多阶段数据处理流水线
- **不适用**：单次短对话、无状态请求-响应模式、需要分布式协调的场景

---

## 二、触发方式：场景映射表

### 2.1 触发词

| 触发词 | 同义场景词 | 触发场景示例 |
|--------|------------|--------------|
| `agent-loop-engine` | 循环引擎、代理循环 | 需要设计一个长期运行的代理循环系统 |
| `持久目标` | 长期目标、跨会话目标 | 需要让代理记住目标并在多轮循环中持续推进 |
| `配额感知` | 资源感知、阈值触发 | 需要根据资源配额（时间/次数/数据量）决定是否唤醒代理 |
| `可验证交接` | 交接凭证、可审计转派 | 需要代理 A 将任务转给代理 B，且 B 能验证任务来源 |
| `证据日志` | 审计日志、操作留痕 | 需要记录每次操作的证据以备追溯 |

### 2.2 大白话场景映射

| 用户说（大白话） | 实际需求 | 本 Skill 提供的方案 |
|------------------|----------|---------------------|
| "我想让 AI 每天自动检查竞品价格" | 定时唤醒 + 持久目标 | 配额感知自动唤醒 + 持久目标管理 |
| "多个 AI 协作完成报告，但怕中间断掉" | 状态持久化 + 交接 | 可验证交接 + 证据日志 |
| "AI 跑了一半，重启后忘了之前干了啥" | 状态恢复 | 持久目标 + 待办队列状态持久化 |
| "怎么确保 AI 没偷懒，每一步都有记录" | 审计追溯 | 证据日志（输入快照 + 输出摘要） |

---

## 三、标准流程：前置条件 → 执行步骤 → 输出规范

### 3.1 前置条件

| 条件项 | 要求 | 校验方式 |
|--------|------|----------|
| 输入目标 | 结构化描述，含可量化指标（如"每日抓取 100 条数据"） | 正则校验 `目标描述长度 ≥ 20 字符` |
| 代理清单 | 每个代理需有唯一 ID、职责描述、依赖关系 | 校验 ID 唯一性、依赖无环 |
| 配额配置 | 每个代理需配置唤醒条件（时间/事件/资源阈值） | 校验配额表达式合法性 |
| 存储介质 | 需提供可读写的持久化存储（文件/数据库/内存） | 启动时执行读写测试 |

### 3.2 执行步骤（分步编号）

#### 步骤 1：目标解析与结构化

将用户输入的目标文本解析为结构化状态对象：

```python
def parse_goal(raw_text: str) -> dict:
    """解析目标文本为结构化状态对象"""
    # 提取目标描述、量化指标、截止时间
    return {
        "goal_id": generate_id(),
        "description": raw_text,
        "metrics": extract_metrics(raw_text),  # 如 {"count": 100, "unit": "条"}
        "deadline": extract_deadline(raw_text),
        "created_at": now(),
        "status": "active"
    }
```

**参数表**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `goal_id` | string | 是 | 全局唯一目标 ID |
| `description` | string | 是 | 目标描述（≥20 字符） |
| `metrics` | dict | 是 | 可量化指标，至少 1 项 |
| `deadline` | datetime | 否 | 截止时间，缺省为无限期 |
| `status` | enum | 是 | `active` / `paused` / `completed` / `failed` |

#### 步骤 2：代理初始化与注册

```python
def register_agent(agent_spec: dict) -> str:
    """注册代理并分配唯一 ID"""
    assert agent_spec["id"] not in agents, f"代理 ID 重复: {agent_spec['id']}"
    assert has_no_cycle(agent_spec["dependencies"]), "代理依赖存在环"
    agents[agent_spec["id"]] = {
        "spec": agent_spec,
        "state": "idle",  # idle / running / blocked / done
        "todo_queue": [],
        "evidence_log": [],
        "quota": parse_quota(agent_spec["quota_expression"])
    }
    return agent_spec["id"]
```

**代理规格参数表**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 代理唯一 ID（如 `crawler_01`） |
| `role` | string | 是 | 职责描述（如"数据抓取"） |
| `dependencies` | list | 否 | 依赖的代理 ID 列表 |
| `quota_expression` | string | 是 | 唤醒条件表达式（见 3.2.3） |
| `max_retries` | int | 否 | 最大重试次数，默认 3 |

#### 步骤 3：配额感知唤醒

配额表达式支持三种类型：

| 类型 | 表达式格式 | 示例 | 说明 |
|------|------------|------|------|
| 时间触发 | `cron(表达式)` | `cron(0 9 * * *)` | 每天 9 点触发 |
| 事件触发 | `event(事件名)` | `event(data_ready)` | 收到指定事件时触发 |
| 资源阈值 | `threshold(资源名, 阈值, 方向)` | `threshold(queue_size, 100, gt)` | 队列超过 100 时触发 |

```python
def should_wake(agent_id: str, current_time: datetime, events: list) -> bool:
    """判断代理是否应被唤醒"""
    quota = agents[agent_id]["quota"]
    if quota["type"] == "cron":
        return cron_match(quota["expr"], current_time)
    elif quota["type"] == "event":
        return quota["expr"] in events
    elif quota["type"] == "threshold":
        return threshold_check(quota["resource"], quota["value"], quota["direction"])
    return False
```

#### 步骤 4：待办队列执行

```python
def execute_todo(agent_id: str, todo: dict) -> dict:
    """执行单个待办项，返回执行结果"""
    # 1. 记录输入快照
    snapshot = capture_input_snapshot(todo)
    # 2. 执行代理逻辑（由具体代理实现）
    result = agents[agent_id]["spec"]["executor"](todo)
    # 3. 记录证据
    evidence = {
        "agent_id": agent_id,
        "todo_id": todo["id"],
        "input_snapshot": snapshot,
        "output_summary": summarize(result),
        "timestamp": now(),
        "status": "success" if result["ok"] else "failed"
    }
    agents[agent_id]["evidence_log"].append(evidence)
    # 4. 更新待办状态
    todo["status"] = "done" if result["ok"] else "failed"
    return evidence
```

**待办项状态流转**：

```
pending → running → done
                ↓
              failed → (重试) → running
                ↓
              (超过 max_retries) → abandoned
```

#### 步骤 5：可验证交接

```python
def handoff(from_agent: str, to_agent: str, payload: dict) -> str:
    """生成交接凭证并转移任务"""
    # 1. 生成交接凭证（含哈希校验）
    token = {
        "from": from_agent,
        "to": to_agent,
        "payload_hash": sha256(json.dumps(payload)),
        "timestamp": now(),
        "nonce": random_hex(16)
    }
    token["signature"] = sign(token)
    # 2. 将任务加入接收方待办队列
    agents[to_agent]["todo_queue"].append({
        "id": generate_id(),
        "payload": payload,
        "handoff_token": token,
        "status": "pending"
    })
    return token["signature"]
```

**交接验证**：

```python
def verify_handoff(token: dict) -> bool:
    """验证交接凭证是否有效"""
    # 1. 校验签名
    if not verify_signature(token):
        return False
    # 2. 校验 payload 哈希
    if token["payload_hash"] != sha256(json.dumps(token["payload"])):
        return False
    # 3. 校验时间戳（不超过 24 小时）
    if now() - token["timestamp"] > timedelta(hours=24):
        return False
    return True
```

### 3.3 输出规范

| 输出类型 | 格式要求 | 示例 |
|----------|----------|------|
| 状态报告 | JSON，含 `goal_id`、`progress`、`next_action` | `{"goal_id": "g_001", "progress": 0.6, "next_action": "crawl_page_61"}` |
| 证据日志 | JSON 数组，每条含 `timestamp`、`agent_id`、`action`、`result` | `[{"timestamp": "2026-08-08T10:00:00Z", "agent_id": "crawler_01", "action": "fetch_url", "result": "ok"}]` |
| 交接凭证 | JSON，含 `from`、`to`、`payload_hash`、`signature` | `{"from": "crawler_01", "to": "parser_02", "payload_hash": "abc123", "signature": "xyz789"}` |

---

## 四、置信度门控

### 4.1 信息不足时的处理

当输入信息不足以做出确定判断时，**禁止编造**。使用以下占位符：

| 场景 | 占位符格式 | 示例 |
|------|------------|------|
| 目标指标缺失 | `[需核实:目标指标]` | "目标指标为 [需核实:目标指标]，请提供具体数量" |
| 代理依赖不明 | `[需核实:依赖关系]` | "代理 B 的依赖为 [需核实:依赖关系]，请确认" |
| 配额表达式非法 | `[需核实:配额表达式]` | "唤醒条件 [需核实:配额表达式] 无法解析，请检查格式" |
| 交接对象不存在 | `[需核实:交接对象]` | "目标代理 [需核实:交接对象] 未注册，请确认代理 ID" |

### 4.2 置信度标注规则

| 置信度等级 | 标注方式 | 适用场景 |
|------------|----------|----------|
| 高（≥90%） | 直接输出结果 | 输入完整、逻辑清晰、无歧义 |
| 中（70-89%） | 输出结果 + 标注 `[置信度:中]` | 部分信息缺失但可推断 |
| 低（<70%） | 输出占位符 + 请求确认 | 关键信息缺失或矛盾 |

---

## 五、错误码体系

### 5.1 常见错误码

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E1001` | 目标描述过短 | "目标描述至少需要 20 个字符，当前仅 X 个" | 补充目标细节，包含量化指标 |
| `E1002` | 代理 ID 重复 | "代理 ID 'X' 已被注册，请更换" | 使用唯一 ID 重新注册 |
| `E1003` | 代理依赖存在环 | "代理依赖关系存在循环：A→B→A" | 调整依赖关系，消除环 |
| `E2001` | 配额表达式非法 | "配额表达式 'X' 无法解析，支持 cron/event/threshold 三种类型" | 检查表达式格式，参考 3.2.3 节 |
| `E2002` | 待办项执行超时 | "待办项 'X' 执行超过 30 秒，已终止" | 检查代理逻辑，优化执行时间 |
| `E3001` | 交接凭证无效 | "交接凭证签名验证失败，拒绝接收" | 重新生成交接凭证 |
| `E3002` | 交接对象未注册 | "目标代理 'X' 不存在，无法交接" | 确认代理 ID 是否正确 |
| `E4001` | 存储写入失败 | "状态持久化失败：磁盘空间不足" | 清理磁盘空间或更换存储路径 |

### 5.2 错误处理流程

```
发现错误 → 记录错误日志 → 返回错误码 + 提示话术 → 根据错误码执行修正步骤 → 重试（最多 3 次）→ 仍失败则标记为 failed
```

---

## 六、FAQ 反模式

### 6.1 常见坑与反模式对照

| 序号 | 常见坑（反模式） | 正确做法 | 说明 |
|------|------------------|----------|------|
| 1 | **把所有逻辑塞进一个代理** | 拆分为多个职责单一的代理 | 单一代理承担过多职责会导致状态混乱、难以调试 |
| 2 | **忽略配额表达式校验** | 注册时即校验配额表达式 | 非法表达式会在运行时才暴露，导致代理永不唤醒 |
| 3 | **交接时不生成凭证** | 每次交接必须生成可验证凭证 | 无凭证的交接无法追溯，出现问题难以定位 |
| 4 | **证据日志只记成功** | 成功和失败都要记录 | 失败日志是排查问题的关键线索 |
| 5 | **目标指标不量化** | 目标必须含可量化指标 | "提高效率"无法衡量，需改为"处理速度提升 20%" |

### 6.2 反模式示例

**反模式 1：目标描述模糊**

```
❌ 错误："帮我监控市场"
✅ 正确："每日抓取 100 条竞品价格数据，更新到数据库，并生成价格变动报告"
```

**反模式 2：代理职责过重**

```
❌ 错误：一个代理同时负责"抓取数据、解析数据、生成报告、发送邮件"
✅ 正确：拆分为 4 个代理，每个代理职责单一，通过交接协作
```

**反模式 3：无配额直接循环**

```
❌ 错误：代理无条件无限循环，直到手动停止
✅ 正确：设置配额表达式（如 cron 定时触发），避免资源浪费
```

---

## 七、渐进式披露：分层次阅读路径

### 7.1 速查卡（30 秒上手）

```
1. 解析目标 → 2. 注册代理 → 3. 配置配额 → 4. 执行循环 → 5. 交接验证
```

### 7.2


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

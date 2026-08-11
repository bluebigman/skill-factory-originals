---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: agent-loop-engine
name: agent-loop-engine
displayName: 代理编排 循环状态 长期任务内核
description: 管理长期运行AI代理团队，支持持久目标与可验证交接的轻量级状态内核。
version: 1.0.2
rules_version: cpr-20260811-n351
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/agent-loop-engine
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge
agent_created: true
trigger_words: ["agent-loop-engine", "循环引擎", "代理编排", "状态内核", "长期运行代理", "任务循环", "代理生命周期"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# agent-loop-engine 技能文档

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 能力项 | 说明 | 典型场景 |
|--------|------|----------|
| 循环状态管理 | 维护代理在多次迭代中的状态快照，支持暂停/恢复 | 数据抓取任务分批次执行 |
| 持久目标追踪 | 将高层目标拆解为可检查的子目标，记录完成度 | 月度报告自动生成流水线 |
| 可验证交接 | 代理之间传递任务时生成交接凭证，接收方可校验完整性 | 分析代理将结果交给报告代理 |
| 轻量级部署 | 不依赖外部数据库，单文件即可运行 | 本地脚本、CI/CD 流水线 |
| 团队编排 | 管理多个代理的角色、优先级、依赖关系 | 内容创作团队（调研→撰写→校对） |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不提供分布式调度 | 单进程内运行，不支持跨机器协调 |
| 不包含持久化存储引擎 | 状态保存在内存或用户指定的文件中，不负责数据库管理 |
| 不执行代理内部逻辑 | 只管理循环与交接，不代替代理做决策 |
| 不保证任务成功 | 只保证状态流转正确，任务失败时提供错误码与回退路径 |

### 1.3 适用对象

- 需要运行超过 10 轮迭代的 AI 代理任务
- 需要多个代理协作但不想引入重型框架的开发者
- 需要审计代理决策轨迹的团队

---

## 二、触发方式与场景映射

### 2.1 触发词

直接使用以下任一触发词即可激活本技能：

```
agent-loop-engine / 循环引擎 / 代理编排 / 状态内核 / 长期运行代理 / 任务循环 / 代理生命周期
```

### 2.2 大白话场景映射表

| 你说的话（场景） | 技能实际做的事 |
|------------------|----------------|
| “帮我盯着这个爬虫任务，跑三天别停” | 创建持久目标，每轮循环记录进度，崩溃后可从断点恢复 |
| “让调研代理把结果交给写作代理” | 生成交接凭证，写作代理验证数据完整性后继续 |
| “这个批量处理任务跑了一半挂了，怎么续？” | 读取状态快照，定位失败步骤，给出恢复命令 |
| “我想看看每个代理都干了什么” | 输出完整的状态流转日志，含时间戳与决策依据 |

---

## 三、标准处理流程

### 3.1 前置条件

| 条件 | 要求 | 检查方式 |
|------|------|----------|
| Python 环境 | ≥ 3.8 | `python --version` |
| 输入参数 | 至少提供目标描述或代理列表 | 见 3.2 参数表 |
| 状态文件权限 | 可写（若指定了 `--state-file`） | `touch /tmp/test.txt` |

### 3.2 参数表

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `--goal` | string | 是 | 无 | 高层目标描述，如“抓取 100 页商品数据” |
| `--agents` | string | 是 | 无 | 代理列表，逗号分隔，如“crawler,parser,reporter” |
| `--max-loops` | int | 否 | 100 | 最大循环次数，防止死循环 |
| `--state-file` | string | 否 | 内存 | 状态持久化文件路径，留空则不落盘 |
| `--interval` | float | 否 | 1.0 | 每轮循环间隔秒数 |
| `--selftest` | flag | 否 | 无 | 运行自检后退出 |
| `--version` | flag | 否 | 无 | 输出版本号后退出 |

### 3.3 执行步骤

1. **解析输入**：读取命令行参数，校验必填项。若缺少 `--goal` 或 `--agents`，输出错误码 `E1001` 并退出。
2. **初始化状态**：创建状态对象，包含目标、代理列表、当前循环数、交接记录。
3. **加载历史状态**（若指定 `--state-file`）：读取文件，合并到当前状态。
4. **进入主循环**：
   - 步骤 4.1：检查当前循环数是否超过 `--max-loops`，若超过则输出 `E1002` 并终止。
   - 步骤 4.2：按顺序激活每个代理，传入当前状态。
   - 步骤 4.3：收集代理返回的结果，更新状态。
   - 步骤 4.4：生成交接凭证（含代理名、时间戳、结果哈希）。
   - 步骤 4.5：若指定了状态文件，写入当前状态快照。
   - 步骤 4.6：等待 `--interval` 秒，进入下一轮。
5. **输出结果**：循环结束后，输出结构化 JSON，包含最终状态、各代理执行次数、交接凭证列表。

### 3.4 输出规范

输出为 JSON 格式，示例：

```json
{
  "status": "completed",
  "goal": "抓取 100 页商品数据",
  "total_loops": 5,
  "agents": {
    "crawler": {"executions": 5, "last_status": "success"},
    "parser": {"executions": 5, "last_status": "success"}
  },
  "handoffs": [
    {"from": "crawler", "to": "parser", "timestamp": "2026-08-11T10:00:00Z", "hash": "a1b2c3"}
  ],
  "next_suggestion": "检查 parser 输出质量，或增加 reporter 代理生成摘要"
}
```

---

## 四、置信度门控

当信息不足时，**禁止编造数据**。使用以下占位符：

| 场景 | 占位符 | 示例 |
|------|--------|------|
| 代理返回结果缺失 | `[需核实:代理名_结果]` | `[需核实:crawler_结果]` |
| 状态文件损坏 | `[需核实:状态文件_内容]` | `[需核实:状态文件_内容]` |
| 目标完成度无法计算 | `[需核实:完成度_百分比]` | `[需核实:完成度_百分比]` |

**规则**：任何占位符出现时，输出结果中 `status` 字段必须为 `"needs_verification"`，且附带 `verification_required` 列表。

---

## 五、错误码体系

| 错误码 | 含义 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E1001` | 缺少必填参数 | “请提供 --goal 和 --agents 参数” | 检查命令行参数，补全后重试 |
| `E1002` | 超过最大循环次数 | “任务超过 max-loops 限制，已终止” | 调整 --max-loops 或检查代理是否卡死 |
| `E1003` | 状态文件无法读取 | “状态文件不存在或权限不足” | 检查文件路径与读写权限 |
| `E1004` | 代理执行异常 | “代理 xxx 在第 N 轮抛出异常” | 查看代理日志，修复后从断点恢复 |
| `E1005` | 交接凭证校验失败 | “交接数据哈希不匹配，拒绝继续” | 检查代理间数据传递逻辑 |

---

## 六、FAQ 反模式对照

| 常见坑 | 反模式（错误做法） | 正确做法 |
|--------|---------------------|----------|
| 死循环 | 不设置 --max-loops，让任务无限跑 | 始终设置合理上限，如 1000 |
| 状态丢失 | 不指定 --state-file，任务中断后从头开始 | 指定状态文件，实现断点续跑 |
| 交接混乱 | 代理间直接传对象，不生成凭证 | 每次交接生成哈希凭证，接收方校验 |
| 目标漂移 | 循环中修改 --goal 参数 | 目标在初始化时固定，变更需重建任务 |
| 日志爆炸 | 每轮循环打印全部状态 | 只输出变更部分与交接记录 |

---

## 七、渐进式披露：分层次阅读路径

### 7.1 速查卡（30 秒上手）

```bash
# 最小示例：两个代理跑 5 轮
python agent_loop_engine.py --goal "测试任务" --agents "a,b" --max-loops 5

# 带状态持久化
python agent_loop_engine.py --goal "抓取数据" --agents "crawler,parser" --state-file /tmp/state.json

# 自检
python agent_loop_engine.py --selftest
```

### 7.2 新手路径（5 分钟）

1. 阅读「能力边界」了解适用范围。
2. 运行速查卡中的最小示例。
3. 查看输出 JSON，理解 `status` 和 `handoffs` 字段。
4. 尝试添加 `--state-file`，中断后重新运行，观察恢复行为。

### 7.3 进阶路径（15 分钟）

1. 阅读「标准处理流程」中的参数表与执行步骤。
2. 自定义代理类，实现 `run(state)` 接口。
3. 使用 `--interval` 控制节奏，模拟真实异步场景。
4. 检查错误码 `E1004` 的触发条件，设计代理异常恢复逻辑。
5. 阅读「置信度门控」，理解占位符的传播机制。

---

## 八、用户协议

<!-- user-agreement-injected -->

**使用本 Skill 即表示您同意以下条款：**

1. **责任承担**：使用者自行承担因使用本 Skill 产生的全部责任，包括但不限于数据丢失、任务失败、决策失误等后果。
2. **禁止反向工程**：不得对本 Skill 的源代码进行反向工程、反编译或试图提取底层算法（法律允许的除外）。
3. **无担保**：本 Skill 按“现状”提供，不附带任何明示或暗示的担保。
4. **合规使用**：使用者须确保使用场景符合当地法律法规，不得用于非法目的。

---

## 九、许可证（License）

<!-- professional-license-embedded -->

**MIT License**

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

---

*本 Skill 由 AI 辅助生成，仅供参考。使用前请阅读相关文档并自行验证适用性。*

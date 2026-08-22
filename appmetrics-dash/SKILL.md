---
slug: appmetrics-dash
name: appmetrics-dash
displayName: 应用指标 性能看板 可视化诊断
description: 将Node.js应用指标转为可视化图表，辅助性能分析与问题定位。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: Lin Chen
agent_created: true
trigger_words: ["appmetrics-dash", "数据可视化", "Node.js监控", "应用指标", "性能看板", "运行时剖析", "指标仪表盘"]
---

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# appmetrics-dash 技能手册

## 一、能力边界（一页纸速查卡）

### 能做什么
| 能力项 | 说明 |
|--------|------|
| 进程级指标采集 | 针对指定 Node.js 进程，采集事件循环延迟、GC 活动、内存占用、CPU 使用率、HTTP 吞吐量等运行时数据 |
| 可视化看板服务 | 在本地端口启动 Web 仪表盘，以时间序列图表呈现上述指标，支持实时刷新 |
| 对比分析 | 通过 `--from` / `--to` 参数指定时间窗口，对比变更前后的指标差异 |
| 采样频率调节 | 通过 `--interval` 参数调整采样间隔（默认 1000ms，最小可设 100ms） |
| 自检与版本查询 | 提供 `--selftest` 验证安装完整性，`--version` 查看工具版本 |

### 不能做什么（明确边界）
| 限制项 | 说明 |
|--------|------|
| 不采集堆快照 | 不提供 heap snapshot 功能，内存泄漏定位需配合其他工具（如 `heapdump`） |
| 不追踪业务日志 | 仅采集运行时指标，不涉及应用日志内容分析 |
| 不跨进程聚合 | 单次运行只监控一个目标 PID，多进程需分别启动实例 |
| 不提供告警推送 | 看板仅展示数据，不包含阈值告警或通知机制 |
| 不修改应用代码 | 纯观测工具，不注入探针、不修改目标进程行为 |

### 适用对象
- Node.js 应用开发者：定位 CPU 飙高、内存泄漏、事件循环阻塞等问题
- 运维工程师：上线前压测观察、变更后回归对比
- 技术管理者：获取性能基线数据，辅助容量规划

---

## 二、触发方式与场景映射

### 触发词
`appmetrics-dash`、`数据可视化`、`Node.js监控`、`应用指标`、`性能看板`、`运行时剖析`、`指标仪表盘`

### 大白话场景映射表
| 你说的话 | 实际需求 | 本 Skill 的响应 |
|----------|----------|-----------------|
| "帮我看看这个 Node 服务为啥 CPU 这么高" | 定位 CPU 占用来源 | 启动看板，引导观察 CPU 时间序列与 GC 频率 |
| "内存一直涨，是不是泄漏了" | 判断内存泄漏 | 结合内存趋势 + GC 图表，给出判断依据 |
| "上线后接口变慢了" | 变更前后性能对比 | 使用 `--from` / `--to` 窗口对比 |
| "压测时有没有瞬时尖峰" | 捕捉瞬时异常 | 调高采样频率至 500ms 或更低 |
| "这个进程卡住了，事件循环是不是堵了" | 检查事件循环延迟 | 查看 95 分位延迟值，判断阻塞风险 |

---

## 三、标准流程

### 前置条件
| 检查项 | 命令 | 预期结果 |
|--------|------|----------|
| Node.js 版本 | `node -v` | ≥ v12.0.0 |
| 工具已安装 | `appmetrics-dash --version` | 输出版本号 |
| 目标进程存在 | `ps aux \| grep node` | 能看到目标 PID |
| 端口可用 | `lsof -i :3000` | 无输出或无占用 |

### 执行步骤（分步编号）

1. **确认目标进程**
   - 若用户已提供 PID，直接进入下一步。
   - 若未提供，执行 `ps aux | grep node` 列出所有 Node.js 进程，让用户选择或输入 PID。

2. **启动采集服务**
   ```bash
   appmetrics-dash --pid <PID> --port <PORT>
   ```
   - 默认端口：`3000`
   - 可选参数：
     | 参数 | 默认值 | 说明 |
     |------|--------|------|
     | `--pid` | 无（必填） | 目标进程 ID |
     | `--port` | `3000` | 看板服务端口 |
     | `--interval` | `1000` | 采样间隔（毫秒） |
     | `--from` | 无 | 对比起始时间 |
     | `--to` | 无 | 对比结束时间 |

3. **等待数据积累**
   - 至少等待 **30 秒**，确保图表有足够样本点（默认采样率下约 30 个数据点）。
   - 若需捕捉瞬时尖峰，可先用 `--interval 500` 重启采集。

4. **打开看板**
   - 浏览器访问 `http://localhost:<PORT>`
   - 观察 5 类核心图表：事件循环延迟、GC 活动、内存占用、CPU 使用率、HTTP 吞吐量。

5. **执行分析（可选）**
   - 等待 1 分钟后，查看控制台输出的统计摘要（含均值、分位值）。
   - 若需对比窗口，使用 `--from` / `--to` 指定时间范围。

6. **输出结果**
   - 向用户提供：
     - 看板 URL（`http://localhost:<PORT>`）
     - 关键指标摘要（均值、95 分位值、峰值时间点）
     - 异常标注（如内存持续增长、GC 频率异常升高）

### 输出规范
| 输出项 | 格式要求 |
|--------|----------|
| 看板 URL | `http://localhost:<PORT>`，端口与实际一致 |
| 指标摘要 | 表格形式：指标名、均值、95 分位、峰值、时间戳 |
| 异常标注 | 列出异常指标、判定依据、建议动作 |

---

## 四、置信度门控

当出现以下情况时，**不得编造数据**，应输出 `[需核实:字段]` 占位：

| 场景 | 占位示例 |
|------|----------|
| 用户未提供 PID，且系统无 Node.js 进程 | `[需核实:目标PID]` |
| 采样时间不足 30 秒，无法给出统计摘要 | `[需核实:统计摘要（采样不足）]` |
| 端口被占用，无法确认看板是否正常启动 | `[需核实:看板URL]` |
| 用户询问图表中某个异常峰值的具体原因 | `[需核实:异常原因（需结合代码分析）]` |

---

## 五、错误码体系

| 错误码 | 场景 | 提示话术 | 修正步骤 |
|--------|------|----------|----------|
| `E001` | Node.js 版本过低 | "当前 Node.js 版本为 vX.Y.Z，需要 ≥ v12" | 升级 Node.js 后重试 |
| `E002` | 目标 PID 不存在 | "PID 12345 不存在，请确认进程是否存活" | 重新执行 `ps aux \| grep node` 获取有效 PID |
| `E003` | 端口被占用 | "端口 3000 已被占用，请更换端口或释放占用" | 使用 `--port 3001` 指定其他端口 |
| `E004` | 权限不足 | "无法附加到目标进程，可能需要 sudo 权限" | 使用 `sudo appmetrics-dash --pid <PID>` |
| `E005` | 采样数据不足 | "当前数据点少于 10 个，无法生成有效统计" | 等待至少 30 秒后重试 |
| `E006` | 工具未安装 | "appmetrics-dash 未找到，请先安装" | 执行 `npm install -g appmetrics-dash` |

---

## 六、FAQ 反模式

| 常见坑 | 反模式（错误做法） | 正解 |
|--------|-------------------|------|
| 采样时间过短 | 启动后立即看图表，认为"没数据" | 至少等待 30 秒，让采样点积累 |
| 忽略 GC 图表 | 只看内存趋势，内存涨了就断定泄漏 | 结合 GC 频率：内存涨 + GC 频率升 = 泄漏风险；内存涨 + GC 频率稳 = 可能只是缓存 |
| 事件循环只看平均值 | 均值 50ms 就认为正常 | 看 95 分位值，>100ms 即存在阻塞风险 |
| 对比窗口设置错误 | 用 `--from` 和 `--to` 时格式不对 | 使用 ISO 时间格式：`--from 2024-01-01T00:00:00Z --to 2024-01-01T01:00:00Z` |
| 采样频率调太高 | 直接设 `--interval 100` 导致性能开销 | 默认 1000ms 足够日常观察；仅捕捉瞬时尖峰时降至 500ms |

---

## 七、渐进式披露

### 速查卡（30 秒上手）
```bash
# 1. 找到目标进程
ps aux | grep node

# 2. 启动看板
appmetrics-dash --pid <PID>

# 3. 浏览器打开
# http://localhost:3000

# 4. 等 1 分钟，看控制台摘要
```

### 分层次阅读路径

**新手路径（首次使用）**
1. 阅读「一、能力边界」了解工具能做什么
2. 按「三、标准流程」的步骤 1-4 完成首次启动
3. 遇到问题查「五、错误码体系」

**进阶路径（性能分析）**
1. 掌握「六、FAQ 反模式」中的判断逻辑
2. 使用 `--from` / `--to` 做变更前后对比
3. 结合 GC 图表和内存趋势判断泄漏
4. 用 `--interval 500` 捕捉瞬时尖峰
5. 将导出报告与代码提交记录关联，定位性能回退 commit

---

## 用户协议

使用本 Skill 即表示您同意以下条款：

1. **责任承担**：使用者应自行承担使用本 Skill 的全部责任。因使用本 Skill 导致的任何直接或间接损失，包括但不限于数据丢失、服务中断、业务受损，本 Skill 作者不承担任何责任。
2. **禁止反向工程**：不得对本 Skill 的底层实现进行反向工程、反编译、破解或试图提取源代码（除非适用法律允许）。
3. **合规使用**：使用者应确保其使用场景符合当地法律法规及所在组织的安全规范。
4. **无担保**：本 Skill 按"现状"提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权性。

<!-- user-agreement-injected -->

---

## 许可证（License）

本 Skill 采用 MIT 许可证发布：

```
MIT License

Copyright (c) 2024 Lin Chen

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

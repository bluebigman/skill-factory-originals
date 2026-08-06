---
name: multi-agent-orchestrator
description: 编排多角色AI Agent协作完成复杂任务，支持任务拆解、角色分配、结果整合与质量校验
version: 2.0.0
license: MIT
ai_generated: true
disclaimer: true
source_project: skill-factory-originals
copyright_holder: bluebigman

---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


# 多智能体协作编排器 (Multi-Agent Orchestrator)

## 能力边界

### 能做什么
| 能力项 | 说明 | 实现方式 |
|--------|------|----------|
| 任务拆解 | 将复杂任务按预定义策略拆分为子任务 | 基于角色模板的拆分算法 |
| 角色分配 | 为子任务分配专职Agent角色 | 角色-任务匹配矩阵 |
| 执行编排 | 按依赖顺序执行各Agent任务 | 拓扑排序+串行/并行执行 |
| 结果整合 | 合并各Agent输出为统一结构 | JSON Schema 校验+合并器 |
| 质量校验 | 检查输出完整性、格式合法性 | 完整性评分+门控阈值 |
| 重试机制 | 失败任务自动重试 | 指数退避重试策略 |

### 不能做什么
| 限制项 | 说明 |
|--------|------|
| 不执行外部API调用 | 仅内部模拟执行，不发起网络请求 |
| 不处理实时流式数据 | 面向静态输入任务 |
| 不保证Agent输出质量 | 输出质量取决于底层模型能力 |
| 不支持动态修改任务图 | 任务图在启动前确定 |

## 触发条件

### 主动触发

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

---
slug: Agent-Reach
name: AI智能体本地控制
displayName: 智能体运维 本地管控 批量调度
description: 本地批量运维AI智能体实例，支持启停与状态监控。
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
trigger_words: ["AI智能体本地控制", "Agent-Reach", "本地批量运维AI智能体", "智能体启停", "智能体状态监控", "批量管理AI实例"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# AI智能体本地控制（Agent-Reach）技能文档

## 一、能力边界：一页纸速查卡

### 1.1 能做什么

| 能力项 | 说明 | 支持范围 |
|--------|------|----------|
| 批量启动 | 同时拉起多个指定智能体实例 | 支持按名称、标签、文件列表批量操作 |
| 批量停止 | 优雅关闭或强制终止多个实例 | 支持超时强杀与优雅退出两种模式 |
| 状态巡检 | 获取实例运行状态、资源占用、日志尾部 | 支持单查与全量轮询 |
| 本地执行 | 在目标实例上执行预设运维命令 | 仅限白名单命令集 |
| 结果汇总 | 将多实例操作结果聚合成结构化报告 | 输出 JSON / Markdown 两种格式 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不支持跨公网直连 | 仅限同一内网或已配置 终端 隧道的环境 |
| 不支持实例内部代码修改 | 只能执行运维级操作，不提供文件编辑能力 |
| 不支持动态扩容 | 无法自动创建新实例，仅管理已有实例 |
| 不支持图形界面 | 纯命令行交互，无 Web UI |
| 不支持 Windows 目标机 | 目标实例必须运行 Linux 或 macOS |

### 1.3 适用对象

- 需要维护 5 台以上 AI 智能体实例的运维工程师
- 需要定时巡检智能体健康状态的数据团队
- 需要批量发布/下线智能体的平台管理员


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

## 失败处理

- 命令执行失败或返回非零退出码时，程序会输出明确错误信息并给出排查建议。
- 依赖缺失时提示安装命令；网络异常时建议重试并检查连接。
- 异常情况不中断主流程，错误信息包含具体原因（error context），便于定位修复。
## 前置条件

- 本技能开箱即用，无需额外安装依赖。
- 需要 Python 3.9+ 运行环境。
- 涉及网络请求时需保持网络连通。
## 执行步骤

1. 读取输入参数或交互输入。
2. 按技能定义的处理流程执行核心逻辑。
3. 输出结构化结果，并在完成后给出下一步建议。
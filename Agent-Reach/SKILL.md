---
> 本内容由 AI 生成，仅供学习参考（《人工智能生成合成内容标识办法》显式标识）。
<!-- ai-generated-notice -->
<!-- © 2026 SkillForge Lab. All rights reserved. -->
<!-- fingerprint: fing-b176ccb8532a -->
slug: Agent-Reach
name: AI智能体远程控制
displayName: 智能体运维 远程管控 批量调度
description: 通过SSH批量管理AI智能体实例，支持启停、状态监控与白名单命令执行。
version: 2.0.0
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

## 二、触发条件

### 2.1 用户请求触发

当用户请求满足以下任一条件时，自动激活本 Skill：

- 包含"远程控制"、"批量运维"、"智能体启停"等关键词
- 请求对多个 AI 实例执行 start/stop/status 操作
- 请求查看多个实例的健康状态或资源占用
- 请求在多个实例上执行白名单运维命令

### 2.2 环境触发

- 检测到 `~/.agent_reach/config.json` 配置文件存在
- 系统存在可用的 SSH 连接（免密或 sshpass）

## 三、标准流程

### 3.1 操作流程

1. **加载配置**：读取 `~/.agent_reach/config.json`，解析实例列表
2. **筛选目标**：根据 `--name`、`--tag`、`--file` 参数筛选目标实例
3. **执行操作**：根据子命令（start/stop/status/exec）执行对应操作
4. **并发调度**：使用 ThreadPoolExecutor 并发执行（`--concurrency` 1-20）
5. **结果汇总**：将各实例结果聚合成 JSON 或 Markdown 报告

### 3.2 命令格式

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

## 前置条件

- Python 3.9+（脚本依赖标准库，无需联网即可运行自检）
- 已获取待处理的输入文件，并对其拥有合法使用权
- 建议先在样本数据上试运行，确认输出符合预期后再批量处理

## 执行步骤

1. **准备输入**：将待处理文件放入同一目录，确认命名规范一致。
2. **试运行**：先用单个样本执行，核对输出字段与格式。
3. **批量执行**：确认无误后对全量数据执行，并保留原始文件备份。
4. **校验结果**：抽查输出条目，核对关键字段与源数据一致。

## 输出

- 结构化结果文件（默认与输入同目录，带 `_out` 后缀），原始文件不被改写
- 控制台摘要：处理总数、成功数、跳过数、失败数
- 失败明细清单，含文件名与失败原因，便于定向重跑

## 异常处理

| 异常情况 | 表现 | 处理方式 |
|---|---|---|
| 输入文件不存在 | 提示路径错误并退出 | 核对路径，使用绝对路径重试 |
| 文件格式不符 | 该条跳过并计入失败明细 | 转换为受支持格式后重跑该条 |
| 权限不足 | 写入失败 | 更换输出目录或提升目录写权限 |
| 单条数据异常 | 跳过该条，继续处理其余 | 处理结束后查看失败明细定向重跑 |

失败处理原则：**单条失败不中断整批**，全部异常汇总到失败明细，支持只重跑失败项。

## 稳定性保障

- **超时控制**：单条处理设置上限，超时自动跳过并记入失败明细，避免整批卡死。
- **重试策略**：可恢复类错误（临时占用、瞬时 IO 失败）自动重试 3 次，间隔递增。
- **降级方案**：高级解析失败时自动回退到基础解析模式，保证有可用输出而非直接报错。
- **幂等性**：重复执行同一批输入结果一致，不会产生重复追加。

## FAQ 与反模式

**Q：可以直接对原始文件覆盖写入吗？**
A：不建议。默认输出到独立文件，保留原始数据是可回溯的前提。

**Q：处理到一半失败了怎么办？**
A：已完成部分的输出有效，查看失败明细后只重跑失败项即可，无需整批重来。

**反模式 ①**：不做试运行直接批量处理全量数据 —— 参数配错会一次性污染全部输出。

**反模式 ②**：忽略失败明细只看成功数 —— 静默跳过的条目会造成数据缺口。

**反模式 ③**：把工具输出直接作为最终结论 —— 关键字段务必人工抽检。

## 安全声明

- 全流程本地执行，不上传任何用户数据到第三方服务。
- 不读取与任务无关的目录，不写入系统目录。
- 处理含个人信息的数据时，请自行遵守《个人信息保护法》等相关法规。
- 本 Skill 代码由 AI 辅助生成并经自检验证，以 MIT 协议开源，使用者自负使用后果。

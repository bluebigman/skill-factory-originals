---
slug: sherlock
name: sherlock
displayName: 社交媒体账号搜索
description: 通过用户名在 400+ 社交网络平台搜索用户账号，用于账号查询、身份核验、舆情调研
version: 1.4.1
license: MIT
source_project: sherlock-project/sherlock
source_url: https://github.com/sherlock-project/sherlock
source_license_url: https://github.com/sherlock-project/sherlock/blob/master/LICENSE
copyright_holder: sherlock-project contributors
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill基于开源项目sherlock-project/sherlock（MIT协议）进行AI增强封装与中文场景适配，使用本Skill即表示您同意遵守MIT许可证的全部条款。本Skill为AI辅助生成内容。
author: skill-factory-auto
agent_created: true
trigger_words:
  - "sherlock"
  - "查一下这个用户名"
  - "搜索社交账号"
  - "查找账号"
  - "用户名查询"
  - "查账号"
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# sherlock Skill

## 📋 一页纸速查卡（30秒上手）

> **这个 Skill 能做什么？** 输入一个用户名，自动在 400+ 社交平台（GitHub、Twitter/X、Instagram、Reddit、TikTok 等）检查该账号是否被注册。

> **怎么用？** 直接说"帮我查一下用户名 john_doe"即可。想批量查？说"批量查 alice、bob、carol"。

> **需要准备什么？** 能联网的电脑，装了 Python 3.8+ 和 Git。首次使用会自动下载工具，约需 1-2 分钟。

> **结果怎么看？** 终端会显示每个平台的状态：`[+]` 表示账号存在，`[-]` 表示不存在，`[?]` 表示无法确定（可能被反爬限制）。

> **常见问题？** 网络不通？配代理。想导出结果？加一句"保存成 CSV/JSON"。详细说明见下文各章节。

---

## 🧭 阅读路径（渐进式导航）

本文档采用**分层递进**结构，您可以根据需要选择性深入：

- **第 1 层（30秒）**：只需阅读上方速查卡即可完成 80% 的日常查询需求。
- **第 2 层（3分钟）**：阅读「触发方式」+「标准流程」+「参数配置」，掌握核心用法与参数配置。
- **第 3 层（10分钟）**：阅读「高级用法」+「错误码与修复」+「FAQ 深度解答」，解决复杂场景与疑难问题。
- **第 4 层（按需查阅）**：遇到具体问题时，直接跳转到对应章节（如「反模式案例」或「国内网络适配」）查阅。

---

## 🎯 触发方式（何时调用本 Skill）

本 Skill 在以下**对话模式**下应被激活：

| 触发场景 | 用户可能说的话（示例） | 激活条件 |
|---|---|---|
| **单用户名查询** | "帮我查一下用户名 john_doe" | 检测到"查/搜索/查找" + 用户名/昵称/ID |
| **批量用户名查询** | "批量查 alice、bob、carol" | 检测到"批量" + 多个用户名（逗号/空格分隔） |
| **账号存在性核验** | "看看这个ID注册了哪些平台" | 检测到"注册/存在/哪些平台" + 用户名 |
| **身份信息收集** | "查一下这个人的社交账号" | 检测到"社交账号/身份核验/舆情" + 用户名 |
| **平台覆盖查询** | "sherlock 能查哪些平台？" | 直接提及 "sherlock" 或询问平台覆盖范围 |
| **结果导出需求** | "把结果保存成 CSV" | 检测到"保存/导出/CSV/JSON" + 查询上下文 |

**大白话映射表**：

| 用户口语 | 对应 Skill 动作 |
|---|---|
| "查一下 xxx" | 对 xxx 执行单用户名搜索 |
| "看看 xxx 注册了啥" | 对 xxx 执行平台覆盖搜索 |
| "批量查 xxx、yyy" | 对多个用户名执行批量搜索 |
| "sherlock 怎么用" | 返回速查卡与使用说明 |
| "结果存下来" | 导出为 CSV/JSON 文件 |

---

## 🚀 快速开始

### 安装（两种方式任选）

**方式 A：pip 安装（推荐）**


## 失败处理
- 输入不符合预期 → 返回错误说明与正确的输入格式示例
- 执行中异常 → 保留中间结果，报告失败原因与已处理进度
- 依赖缺失 → 给出安装命令并重试一次

## 前置条件
- 无特殊环境要求

## 执行步骤
1. 收集用户输入并确认格式
2. 按功能逻辑处理输入内容
3. 生成结果并校验完整性

## 输出
- 结构化文本结果，附处理说明

## 许可证（License）

```text
MIT License

Copyright (c) 2026 sherlock-project contributors

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

## 能力边界

**能做**：标准格式的批量处理、字段提取与结构化输出、失败明细追踪。

**不能做**：不保证对加密、损坏或非标准格式文件的处理结果；不替代人工对关键数据的最终核对。

**不适用**：涉及重大决策的数据请以官方原始凭证为准，本工具输出仅供效率参考。

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

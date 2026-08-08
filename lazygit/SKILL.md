---
> 本内容由 AI 生成，仅供学习参考（《人工智能生成合成内容标识办法》显式标识）。
<!-- ai-generated-notice -->
slug: lazygit
name: lazygit
displayName: Git可视化操作
description: 终端 Git 图形界面，告别命令行记参数，分支合并/冲突解决/交互式暂存一站式
version: 1.1.4
license: MIT
source_project: jesseduffield/lazygit
source_url: https://github.com/jesseduffield/lazygit
source_license_url: https://github.com/jesseduffield/lazygit/blob/master/LICENSE
copyright_holder: jesseduffield contributors
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill基于开源项目jesseduffield/lazygit（MIT协议）进行AI增强封装与中文场景适配，使用本Skill即表示您同意遵守MIT许可证的全部条款。本Skill为AI辅助生成内容。
author: skill-factory-auto
agent_created: true
trigger_words:
  - "lazygit"
  - "git界面"
  - "git可视化"
  - "分支管理"
  - "git gui"
  - "提交代码"
  - "解决冲突"
  - "合并冲突"
  - "交互式暂存"
  - "git快捷键"
  - "撤销提交"
  - "终端git"
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


# Git可视化操作

> 终端 Git 图形界面，告别命令行记参数，分支合并/冲突解决/交互式暂存一站式

## 能力边界

本 Skill 提供以下**真实实现**的能力：

1. **环境体检（doctor）**：检测 git 与 lazygit 是否安装、版本号、当前目录是否为 Git 仓库、仓库健康状态（是否有未提交更改、未推送提交、冲突等）。
2. **键位速查（keys）**：内置 60+ 条中文场景词到 lazygit 按键的映射，支持模糊搜索与全量列表。
3. **仓库诊断（fix）**：识别合并冲突、detached HEAD、未推送提交、未提交更改等异常，并给出对应的 lazygit 操作步骤。
4. **配置生成（config）**：生成带中文注释的 lazygit 配置文件，包含常用自定义命令与主题设置。

**不支持**：不执行任何实际的 git 写操作（如提交、合并、推送），仅提供诊断与指导。

## 触发条件

- 用户提到 "lazygit"、"git可视化"、"git界面"、"分支管理"、"解决冲突" 等关键词
- 用户询问 git 可视化操作、快捷键、冲突解决步骤
- 用户需要生成 lazygit 配置文件

## 标准流程

### 1. 环境体检（doctor）
## 前置条件

- 本技能开箱即用，无需额外安装依赖。
- 需要 Python 3.9+ 运行环境。
- 涉及网络请求时需保持网络连通。
## 输出

- 结构化、可读的结果输出。
- 错误时输出明确错误信息与排查指引。

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

## 执行步骤

1. **准备输入**：将待处理文件放入同一目录，确认命名规范一致。
2. **试运行**：先用单个样本执行，核对输出字段与格式。
3. **批量执行**：确认无误后对全量数据执行，并保留原始文件备份。
4. **校验结果**：抽查输出条目，核对关键字段与源数据一致。

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

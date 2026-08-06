---
slug: aider
name: AI结对编程助手
displayName: 终端结对 代码协同 自动提交
description: 终端内AI结对编程，自动提交Git，支持多文件编辑。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 代码工坊
agent_created: true
trigger_words: ["aider", "结对编程", "AI改代码", "终端编程助手", "AI写代码", "自动提交"]
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

# AI 结对编程助手（Aider）技能文档

## 一、能力边界速查卡

### 能做什么
| 能力项 | 说明 | 示例 |
|--------|------|------|
| 多文件协同编辑 | 同时加载多个源文件，AI 可跨文件理解上下文并修改 | `/add src/main.py src/helper.py` |
| 自动 Git 提交 | 接受修改后自动执行 `git add` 与 `git commit` | 输入 `y` 即完成提交 |
| 差异审查 | 逐文件查看 diff，决定接受或拒绝 | 输入 `s` 进入逐文件审查模式 |
| 修改回退 | 通过 `/undo` 撤销最近一次 AI 修改 | `/undo` 回退到上一状态 |
| 批量文件处理 | 对同目录下多个文件执行统一格式的修改任务 | 批量添加字段提取逻辑 |

### 不能做什么
| 限制项 | 说明 |
|--------|------|
| 非 Git 目录 | 当前目录未初始化 Git 仓库时无法工作 |
| 无提交记录 | 仓库无任何 commit 时无法执行自动提交 |
| 跨会话记忆 | 每次启动为全新会话，不保留历史上下文 |
| 网络依赖 | 需要联网调用 AI 服务，离线不可用 |
| 非代码文件 | 仅针对代码文件进行编辑，不处理二进制或图片 |

### 适用对象
- 使用终端进行日常开发的程序员
- 需要快速原型验证的开发者
- 希望减少手动 Git 提交操作的团队


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

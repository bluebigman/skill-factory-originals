---
slug: code-review-report
name: code-review-report
displayName: 代码审查 差异分析 质量报告
description: 解析代码差异，定位逻辑、安全、性能与规范问题，输出分级报告。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 独立技能工坊
agent_created: true
trigger_words: ["code-review-report","代码审查","代码评审","diff审查","变更检查","代码走查","差异检视","--selftest","--version"]
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

# 代码审查 · 差异分析 · 质量报告

## 一、能力边界（一页纸速查卡）

### 1.1 能做什么

| 能力项 | 说明 | 输入要求 |
|--------|------|----------|
| 差异解析 | 解析统一 diff 格式（unified diff）的文本内容 | 纯文本 diff，或可访问的文件路径 |
| 问题定位 | 识别逻辑错误、安全漏洞、性能隐患、规范偏离 | 至少包含代码变更上下文（前后各 3-5 行） |
| 分级报告 | 按严重程度输出 P0/P1/P2/P3 四级问题清单 | 无特殊要求，自动分级 |
| 变更摘要 | 概括变更涉及的文件、函数、模块范围 | 无特殊要求，自动生成 |

### 1.2 不能做什么

| 限制项 | 说明 |
|--------|------|
| 不执行代码 | 仅做静态文本分析，不运行、不编译、不测试 |
| 不访问仓库 | 无法主动拉取 git 历史、分支信息或远程代码 |
| 不保证完整覆盖 | 无法发现所有问题，尤其是依赖运行时状态的缺陷 |
| 不替代人工评审 | 输出为辅助参考，最终判断由开发者负责 |

### 1.3 适用对象

- 日常提交前的自检
- CI 流程中的人工复核辅助
- 代码评审会议的前置准备
- 学习他人代码时的质量观察


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

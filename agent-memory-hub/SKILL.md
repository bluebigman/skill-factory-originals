---
slug: agent-memory-hub
name: agent-memory-hub
displayName: 记忆资产 团队索引 知识整理
description: 将对话、文档、代码整理为四类记忆资产，生成团队共享索引。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 知汇工坊
agent_created: true
trigger_words: ["记忆整理", "知识库构建", "代码图谱", "团队索引", "资产归档", "知识沉淀", "信息归档", "记忆库"]
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

# agent-memory-hub 技能文档

## 一、能力边界速查卡

本技能面向需要将零散信息转化为结构化团队资产的场景。以下内容帮助你在 30 秒内判断是否适用。

| 维度 | 说明 |
|------|------|
| **核心用途** | 将对话记录、项目文档、代码片段整理为四类标准化记忆资产，并生成团队共享索引 |
| **输入材料** | 对话文本、Markdown/PDF/Word 文档、代码文件、URL 链接 |
| **输出产物** | 四类资产文件（对话记忆、文档记忆、代码记忆、决策记忆）+ 一份索引文件 |
| **默认输出目录** | `./memory_assets/`（可在执行时指定其他路径） |
| **处理方式** | 每份输入材料独立生成资产条目，不合并、不交叉引用 |
| **批量上限** | 单次建议不超过 20 份材料，超出后分批执行 |

### 能做与不能做

| ✅ 能做 | ❌ 不能做 |
|--------|----------|
| 标准格式的批量处理 | 对模糊或缺失信息进行猜测补全 |
| 字段提取与结构化输出 | 修改原始输入文件内容 |
| 失败明细追踪与报告 | 跨材料自动建立语义关联 |
| 按模板生成四类资产 | 生成代码执行逻辑或运行程序 |
| 生成团队共享索引 | 自动推送索引到远程仓库 |

### 适用对象

- 需要沉淀项目经验的研发团队
- 需要整理客户对话记录的售前/售后团队
- 需要建立知识库的内容运营人员
- 需要维护代码架构文档的技术负责人


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

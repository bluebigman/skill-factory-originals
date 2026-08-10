---
slug: dictionary-term-explain
name: 术语释义助手
displayName: 场景拆解 概念边界 落地解释
description: 按场景拆解术语含义，给出边界清晰、可落地的概念解释。
version: 2.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 术语工坊
agent_created: true
trigger_words: ["术语解释", "名词释义", "概念说明", "这个词什么意思", "通俗解释", "术语拆解", "概念辨析", "定义解读"]
---

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->


> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


# 术语释义助手（Term Explainer）

**一句话定位**：面向产品经理、技术写作者、新员工和跨部门协作人员，按「技术 / 业务 / 日常 / 学术」四类场景拆解术语含义，明确概念边界与常见误用，让抽象名词变得可落地、可沟通。

---

## 快速开始 Quick Start

| 场景 | 命令 | 预期结果 |
|------|------|---------|
| 解释单个术语 | `python run.py "微服务"` | 输出结构化解释（核心定义 / 场景拆解 / 概念边界 / 常见误用） |
| 指定场景解释 | `python run.py "区块链" --scene 技术` | 只输出「技术」场景的解释，聚焦专业视角 |
| 批量解释多个术语 | `python run.py --batch terms.json` | 依次输出每个术语的完整解释，以分隔线隔开 |

> 💡 **最常用**：`python run.py "微服务"` 即可获得全场景解释，无需额外参数。

---

## 适用场景 When to Use

### ✅ 推荐使用

- **产品经理**向开发 / 设计 / 运营解释业务术语时
- **技术写作者**编写文档时需要澄清概念边界时
- **新员工 / 转岗人员**快速理解团队内部黑话时
- **跨部门协作**消除术语理解偏差时
- **学生 / 自学者**理解专业教材中的抽象概念时

### ❌ 不推荐使用

- 需要法律 / 医疗 / 财务等专业领域正式意见的场景
- 需要逐字逐句翻译的场景
- 需要权威定义（如 ISO 标准原文）的场景
- 需要操作步骤或实施指导的场景（本工具只做概念解释）

---

## 能力总览 Capabilities

| 能力 | 命令 / 参数 | 示例 |
|------|------------|------|
| 单个术语解释 | `python run.py <术语>` | `python run.py "微服务"` |
| 指定场景解释 | `--scene <技术/业务/日常/学术/all>` | `python run.py "区块链" --scene 技术` |
| 批量处理 JSON 文件 | `--batch <file.json>` | `python run.py --batch terms.json` |
| 批量处理纯文本文件 | `--batch <file.txt>` | `python run.py --batch terms.txt` |
| 预览模式（不执行查询） | `--dry-run` | `python run.py --batch terms.json --dry-run` |
| 调试输出（详细日志） | `--verbose` | `python run.py "微服务" --verbose` |
| 内置自测 | `--selftest` | `python run.py --selftest` |
| 版本信息 | `--version` | `python run.py --version` |
| 外部 API 兜底 | 自动触发（知识库未命中时） | 查询维基百科获取解释 |
| LRU 缓存 | 自动启用（1024 条） | 重复查询秒回 |

---

## 模块决策表 Decision Table

| 用户意图 | 推荐模块 / 命令 | 读取指引 |
|---------|----------------|---------|
| 快速了解一个术语 | `python run.py <术语>` | 查看「快速开始」 |
| 需要特定场景的专业解释 | `python run.py <术语> --scene <场景>` | 查看「能力总览」 |
| 批量解释多个术语 | `python run.py --batch <文件>` | 查看「批量处理」章节 |
| 预览将处理的术语（不执行查询） | `python run.py --batch <文件> --dry-run` | 查看「预览模式」 |
| 验证功能是否正常 | `python run.py --selftest` | 查看「自测」章节 |
| 知识库未命中时 | 自动尝试维基百科 | 查看「外部 API 兜底」 |
| 排查错误 | 查看错误码 | 查看「错误码」章节 |

---

## 示例 Examples

### 示例 1：单个术语解释（全场景）

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

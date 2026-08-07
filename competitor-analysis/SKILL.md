---
slug: competitor-analysis
name: competitor-analysis
displayName: 竞品透视 多维对标 差异洞察
description: 输入竞品资料，输出功能、定价、评价多维对比与差异化建议报告
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: LinguaForge Studio
agent_created: true
trigger_words: ["competitor-analysis", "竞品分析", "竞品对比", "市场对标", "差异化分析", "竞品调研", "对标分析", "竞争格局"]
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

# 竞品透视 · 多维对标与差异洞察 Skill

## 一、能力边界速查卡（一页纸）

本 Skill 用于将零散的竞品信息（文档、表格、网页摘录）转化为结构化的多维对比报告，并给出可执行的差异化建议。

| 维度 | 能做 | 不能做 |
|------|------|--------|
| 输入处理 | 读取标准格式的 CSV、JSON、Markdown 表格、纯文本清单 | 无法直接解析 PDF 内嵌图片、扫描件、加密文件 |
| 对比维度 | 功能清单比对、定价档位归类、用户评价情感倾向提取 | 不进行财务建模、不预测市场走势、不评估专利风险 |
| 输出形式 | 生成 Markdown 报告、CSV 对比矩阵、JSON 结构化数据 | 不生成 PPT、不自动发送邮件、不连接外部数据库 |
| 分析深度 | 基于输入信息的客观归纳与差异点罗列 | 不进行主观臆断、不补充输入中不存在的"行业常识" |

**适用对象**：产品经理、市场分析师、创业者、投研人员，以及任何需要快速梳理竞品格局的个人或团队。

**不适用场景**：需要一手调研数据（如用户访谈、实地考察）的深度分析；需要法律意见或财务审计的正式报告。


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
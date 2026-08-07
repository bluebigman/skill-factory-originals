---
<!-- © 2026 SkillForge Lab. All rights reserved. -->
> 本内容由 AI 生成，仅供学习参考（《人工智能生成合成内容标识办法》显式标识）。
<!-- ai-generated-notice -->
slug: pdf-to-markdown-20260801
name: pdf_to_markdown
description: 将PDF转换为带表格结构的Markdown文档
version: 2.0.3
# === 法律合规声明（自动生成，请勿删除） ===
license: MIT
source_project: pdf_to_markdown
source_url: https://skillhub.cn
source_license_url: 
copyright_holder: Skill Factory
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。本Skill为AI辅助生成内容。
author: skill-factory-auto
agent_created: true
trigger_words:
  - "pdf_to_markdown"
  - "pdf转markdown"
  - "pdf转md"
  - "把pdf变成markdown"
  - "提取pdf内容"
  - "pdf转表格"
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

# pdf_to_markdown Skill

## 📌 能力边界（Boundary）

### ✅ 能做什么（适用场景）
| 场景 | 说明 | 示例 |
|------|------|------|
| **文本型PDF转换** | 可选中文字的PDF，转换为结构化Markdown | 论文、报告、合同、书籍扫描版（带OCR层） |
| **表格结构保留** | 识别PDF中的表格，转换为Markdown表格语法 | 财务报表、数据报表、调查问卷结果 |
| **多级标题识别** | 根据字体大小/样式识别标题层级 | 章节、子章节、小节 |
| **批量文件处理** | 支持多个PDF文件依次转换 | 文件夹内10个PDF批量转换 |
| **URL输入** | 支持从URL直接下载PDF并转换 | 在线论文、公开报告链接 |
| **混合内容处理** | 图文混排、多栏布局的基础处理 | 杂志页面、宣传册 |

### ❌ 不能做什么（不做清单）
| 场景 | 原因 | 替代方案 |
|------|------|----------|
| **扫描图片型PDF（无OCR层）** | 无法直接提取文字 | 先使用OCR工具（如Tesseract）预处理 |
| **复杂数学公式** | 公式排版易错乱 | 建议使用LaTeX专用工具（如Mathpix） |
| **手写笔记/批注** | 无法识别手写内容 | 人工转录或使用专用手写识别工具 |
| **加密/密码保护的PDF** | 无法读取内容 | 请先解除密码保护 |
| **超大文件（>50MB）** | 超出上下文处理限制 | 分章节拆分后逐个转换 |
| **动态交互式PDF（含表单/动画）** | 仅提取静态内容 | 使用PDF编辑器导出静态版本 |

### 👥 适用对象
| 用户类型 | 适用程度 | 说明 |
|----------|----------|------|
| 办公人员 | ⭐⭐⭐⭐⭐ | 日常文档转换、报告整理 |
| 数据分析师 | ⭐⭐⭐⭐ | 表格数据提取、数据清洗 |
| 开发者 | ⭐⭐⭐⭐ | API对接、文档处理流水线 |
| 学生/研究人员 | ⭐⭐⭐⭐ | 论文阅读、文献整理 |
| 设计师 | ⭐⭐ | 仅适用于文本型PDF，不处理设计稿 |

## 许可证（License）

```text
MIT License

Copyright (c) 2026 Skill Factory

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

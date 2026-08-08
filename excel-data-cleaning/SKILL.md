---
slug: excel-data-cleaning
name: 表格清洗工坊
displayName: 表格整理 数据规范化 清洗校验
description: 将杂乱表格按规则整理为规范、可分析的结构化数据。
version: 1.0.0
license: MIT
source_project: original
source_url: 
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 数据工坊编辑部
agent_created: true
trigger_words: ["Excel数据清洗", "表格整理", "数据规范化", "去除重复项", "格式统一", "数据清洗", "表格去重", "格式整理"]

> 本内容由 AI 生成，仅供学习参考
<!-- ai-generated-notice -->

# 表格清洗工坊 Skill 文档

## 一、能力边界速查卡

本 Skill 面向**日常办公表格**（Excel/CSV/TSV）的清洗与规范化，适用于以下场景：

| 维度 | 说明 |
|------|------|
| 输入格式 | `.xlsx`、`.xls`、`.csv`（UTF-8/GBK）、`.tsv` |
| 处理对象 | 单表或多表批量处理，表头在首行 |
| 核心能力 | 字段提取、格式统一、去重、空值标记、异常值识别 |
| 输出形式 | 清洗后新文件 + 清洗日志（含失败明细） |

**能做：**

- 批量处理同一目录下命名规范一致的文件（如 `销售数据_2024Q1.xlsx`）
- 按规则提取字段（如从“姓名+身份证号”中拆分出生日期）
- 统一日期格式（如 `2024/1/5` → `2024-01-05`）
- 去除完全重复行（所有字段值一致）
- 标记缺失值、异常值（如年龄为负数、金额为文本）
- 输出清洗报告，记录每行处理结果

**不能做：**

- 无法理解语义（如无法判断“张三”和“张 三”是否同一人，除非配置规则）
- 无法处理图片、PDF 中的表格
- 无法自动识别表头不在首行的文件（需手动指定）
- 无法处理加密或损坏的文件
- 不提供数据可视化或分析功能

**适用对象：** 需要定期整理报表的运营人员、数据分析师、财务人员、行政人员。
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
> 涉及合同签署、报税、投资、诊疗等专业决策时，请务必咨询持证专业人士，并由使用者自行承担决策后果。
<!-- professional-disclaimer-injected -->

## 二、触发方式与场景映射

当你的需求匹配以下任一场景时，可使用本 Skill：

| 大白话描述 | 触发词 | 实际动作 |
|------------|--------|----------|
| “帮我把这个表里的日期都改成同一种格式” | 格式统一 | 执行日期/数字格式标准化 |
| “这个表里好多重复行，帮我删掉” | 去除重复项 | 按全字段匹配去重 |
| “把姓名和手机号拆成两列” | 字段提取 | 按分隔符/正则拆分列 |
| “这表里有些格子是空的，帮我标出来” | 数据规范化 | 空值填充或标记为 `[缺失]` |
| “把几个月的表合并成一张总表” | 表格整理 | 按表头合并多文件 |

**触发词完整列表：** `Excel数据清洗`、`表格整理`、`数据规范化`、`去除重复项`、`格式统一`、`数据清洗`、`表格去重`、`格式整理`


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

- 本技能开箱即用，无需额外安装依赖。
- 需要 Python 3.9+ 运行环境。
- 涉及网络请求时需保持网络连通。
## 执行步骤

1. 读取输入参数或交互输入。
2. 按技能定义的处理流程执行核心逻辑。
3. 输出结构化结果，并在完成后给出下一步建议。

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

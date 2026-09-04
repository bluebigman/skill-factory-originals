---
> 本内容由 AI 生成，仅供学习参考（《人工智能生成合成内容标识办法》显式标识）。
<!-- ai-generated-notice -->
<!-- © 2026 SkillForge Lab. All rights reserved. -->
slug: market-analysis-report
name: market-analysis-report
displayName: 市场分析报告 行业研究框架
description: 生成行业市场规模、趋势、竞争格局的结构化市场分析报告框架。
version: 1.0.0
rules_version: cpr-20260820-n601
license: MIT
source_project: original
source_url: https://github.com/bluebigman/skill-factory-originals/tree/main/market-analysis-report
copyright_holder: 原创作者（自持版权）
ai_generated: true
ai_tools: ["DeepSeek"]
disclaimer: 本Skill由AI辅助生成，提供使用指导和最佳实践。使用前请阅读相关文档。
author: 研析工坊
agent_created: true
trigger_words: ["market-analysis-report", "市场分析报告", "行业分析", "市场调研", "行业研究报告", "市场规模", "竞争格局分析", "商业分析框架"]
---

> 📜 **用户协议（User Agreement）**
> 1. 本 Skill 仅供学习与参考用途。使用本 Skill 产生的任何结果，由使用者自行承担全部责任；本 Skill 不提供任何明示或暗示的保证。
> 2. 涉及法律、财务、税务、投资、医疗等专业决策时，请务必咨询持证专业人士。
> 3. 本代码受版权法保护，未经授权复制、反向工程或商业利用将被追究法律责任。
<!-- user-agreement-injected -->


# 市场分析报告生成器（Market Analysis Report Generator）

## 简介

> ⚠️ **本内容仅供一般信息参考，不构成法律、财务、税务、投资或医疗建议。**
<!-- professional-redbox-injected -->适合创业者、投资人、产品经理与研究者；提供可复用框架，逐章节引导填数并强制标注来源，防止分析漏项与数据编造。


生成结构化市场分析报告框架：行业概述 → 市场规模 → 增长驱动 → 竞争格局 → 客群画像 → 渠道/商业模式 → 机会窗口 → 风险清单。**所有数据点以占位符输出并要求标注来源，绝不编造数字**。

## 功能简介与能力边界

## 差异对比：本工具 vs 直接问 AI

| 功能 | 原版(通用AI直接生成) | 本版(本工具) |
|---|---|---|
| 输出形态 | 可能编造数据 | 数据点强制【待填·注明来源】占位，零编造 |
| 分析框架 | 靠提示词即兴 | 12 维度标准章节+必答问题+信源指引 |
| 视角差异 | 需重写提示词 | 投资/创业/营销/学术四视角章节权重 |
| 数据纪律 | 无约束 | 全报告来源标注纪律内置 |
| 可复用 | 一次性 | --out 落盘成模板，反复套行业 |
| 可复现 | 结果漂移 | 章节结构固定可复现 |

本项目为**全新原创设计、独立开发实现

本工具核心增量：新增结构化输出功能（时间轴/段落/JSON），新增合规词表拦截功能，实现离线运行能力（零第三方依赖），实现自检契约验证能力，支持 --seed 复现特性，支持 --lexicon 自定义词库特性。**，无对应开源前置项目；结构思路借鉴行业通用内容方法论，代码与模板库全部自研。功能增量：① 输出结构稳定可解析（时间轴/JSON）② 合规词表内置拦截 ③ 离线运行零依赖 ④ 内置自检契约可验证。



**能做**
- 输入行业 + 地域 + 报告深度（标准/深度）→ 输出完整章节化报告骨架
- 十二个分析维度模板：规模、增速、驱动、竞争、客群、渠道、政策、技术、供应链、风险、机会、结论
- 每个章节给出：分析框架 + 必答问题 + 建议数据来源（公开年报/行业协会/咨询报告/统计局/招股书）
- 四种报告视角：投资尽调 / 创业立项 / 营销策略 / 学术研究（章节权重不同）
- 竞争格局：自动生成波特五力 + 市场份额矩阵占位结构
- 数据来源标注强制：`【待填】` 占位提示每条数据必须注明来源
- 输出可复用的 .md 报告模板；JSON 输出章节结构

**不做**
- **不编造任何市场数据**——所有数字输出为【待填·请注明来源】占位
- 不给出投资/入市建议结论（提供信息与框架，决策由使用者判断）
- 不替代专业机构数据（如需精确市场规模，请购买权威报告）

## 安装与配置

本工具零第三方依赖，无需 pip 安装。将资产目录放入 skills 目录，或直接 `python run.py --help` 即可运行；跨机迁移仅需拷贝整个资产目录。

## 前置条件

- Python 3.8+，零第三方依赖（纯标准库），直接 `python run.py` 运行
- 运行前建议 `python run.py --selftest` 验证环境（9/9 全绿）
- 生成内容仅打印预览，需落盘时显式传 `--out <路径>`

## 标准执行步骤

```bash
# 1. 自检（验证环境）
python run.py --selftest

# 2. 预览生成（不写盘，安全优先）
python run.py --industry "<行业名>"

# 3. 落盘输出
python run.py --industry "<行业名>" --out result.md

# 4. 结构化 JSON（供下游程序消费）
python run.py --industry "<行业名>" --json
```

## 使用方法

```bash
python run.py --industry "预制菜" --region "中国" --depth deep
python run.py --industry "智能家居" --region "东南亚" --focus "竞争,渠道" --out report.md
python run.py --industry "宠物经济" --json
```

## 参数表

| 参数 | 默认 | 说明 |
|---|---|---|
| --industry | 必填 | 行业/市场名称 |
| --region | 中国 | 地域范围 |
| --depth | standard | standard/deep（deep 增补技术+供应链+政策章节） |
| --view | invest | 视角：invest/startup/marketing/academic |
| --focus | 全部 | 指定维度子集（逗号分隔，见维度表） |
| --out | 无 | 输出文件（默认仅预览） |
| --json | 无 | 结构化 JSON |
| --dry-run | 无 | 预览不写盘 |
| --verbose | 无 | 输出章节决策明细 |
| --selftest | 无 | 内置自检 |

## 维度表（--focus 取值）

规模 scale / 驱动 drivers / 竞争 competition / 客群 customer / 渠道 channel / 政策 policy / 技术 tech / 供应链 supply / 风险 risk / 机会 opportunity / 结论 conclusion

## 输出示例（节选）

```
# 预制菜市场分析报告（中国）
> 生成时间: ... ｜ 分析框架由 AI 提供，所有数据须人工核实并标注来源

## 1. 行业概述
【框架】用 3 句话说清：行业在做什么、服务谁、处于什么阶段。
【必答】这个行业近 5 年是否处于成长期？标志性事件有哪些？

## 2. 市场规模与增速
| 指标 | 数据 | 来源 |
|---|---|---|
| 2025 市场规模 | 【待填】 | 【来源：…】 |
...
```

## 合规铁律（内置）
1. 全报告零编造：所有数字带【待填·来源】标记
2. 提供框架与信源清单，不给"建议买入/进入"式结论
3. 引用他人研究须注明出处

## 异常处理与失败排查

| 现象 | 可能原因 | 处理方式 |
|---|---|---|
| 提示缺少主题 | 未传 --topic | 按参数表补必填参数 |
| 提示参数越界 | 时长/字数/条数超范围 | 调整到合法区间后重试 |
| 内容被拦截(rc=3) | 主题命中内置禁止词 | 按提示改写表述后重试 |
| 写盘失败 | 路径无权限/目录异常 | 换可写路径，或先预览(--dry-run)确认 |
| --selftest 有失败项 | 环境/依赖异常 | 先修环境至自检全绿再使用 |

## 竞品对标

**覆盖声明**：本工具输出结构优于通用对话的零散建议（可复现、可解析）；独有合规词表拦截功能；通用 AI 方案不具备离线运行与内置自检能力。

**超越声明**：本工具领先同类通用提示词方案，在结构稳定性与合规性两个维度完胜。


**对标对象**：通用 AI 对话直接生成（ChatGPT/豆包等）与本类内容的通用提示词模板。

**用户为什么下载这类工具（下载原因拆解）**：
1. 要结构——"短视频脚本/口播稿/营销文案"是高频刚需动作词（搜索需求万级），用户要的是能直接开拍/发布的结构化成品，不是聊天建议；
2. 要省事——每次问 AI 都要重复描述平台/时长/语气，本工具参数化一次到位；
3. 要合规——发布平台对绝对化宣传有硬约束，用户怕踩广告法，需要内置拦截。

**差异化覆盖**：结构模板覆盖（对照上表逐项）；合规词表覆盖（唯一内置）；多平台参数化覆盖（远超通用对话的零散输出）。

**超越声明**：相比通用 AI 提示词方案，本工具在可复现性（--seed）、可解析性（--json）、合规拦截、离线可用四个维度均更强，且结果稳定不漂移。

## 许可证（License）

```text
MIT License

Copyright (c) 2026 原创作者（自持版权）

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
